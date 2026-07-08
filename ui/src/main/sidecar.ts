import { spawn, type ChildProcess, type SpawnOptions } from "node:child_process";
import { createServer } from "node:net";
import { setTimeout as delay } from "node:timers/promises";

export const DEFAULT_SIDECAR_HEALTH_TIMEOUT_MS = 10_000;
export const DEFAULT_SIDECAR_POLL_INTERVAL_MS = 150;

type FetchLike = (input: string) => Promise<Response>;
type SpawnProcess = (command: string, args: string[], options: SpawnOptions) => ChildProcess;

export interface SidecarManagerOptions {
  projectPath: string;
  pythonCommand?: string;
  port?: number;
  env?: NodeJS.ProcessEnv;
  healthTimeoutMs?: number;
  pollIntervalMs?: number;
  spawnProcess?: SpawnProcess;
  fetchHealth?: FetchLike;
  pickPort?: () => Promise<number>;
}

export class SidecarStartError extends Error {
  constructor(message: string, options?: ErrorOptions) {
    super(message, options);
    this.name = "SidecarStartError";
  }
}

export const toApiBaseUrl = (port: number): string => `http://127.0.0.1:${port}`;

export const pickFreeLoopbackPort = (): Promise<number> =>
  new Promise((resolve, reject) => {
    const server = createServer();

    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      if (address === null || typeof address === "string") {
        server.close();
        reject(new Error("Failed to allocate a loopback TCP port."));
        return;
      }

      const { port } = address;
      server.close((error) => {
        if (error) {
          reject(error);
          return;
        }
        resolve(port);
      });
    });
  });

const isHealthyPayload = (value: unknown): value is { status: "ok" } =>
  typeof value === "object" &&
  value !== null &&
  "status" in value &&
  (value as { status: unknown }).status === "ok";

export class SidecarManager {
  private child: ChildProcess | null = null;
  private apiBaseUrl: string | null = null;

  constructor(private readonly options: SidecarManagerOptions) {}

  getApiBaseUrl(): string {
    if (this.apiBaseUrl === null) {
      throw new Error("VisionForge API sidecar is not ready.");
    }
    return this.apiBaseUrl;
  }

  async start(): Promise<string> {
    if (this.apiBaseUrl !== null) {
      return this.apiBaseUrl;
    }

    const port = this.options.port ?? (await (this.options.pickPort ?? pickFreeLoopbackPort)());
    const baseUrl = toApiBaseUrl(port);
    const spawnProcess: SpawnProcess = this.options.spawnProcess ?? spawn;
    const pythonCommand =
      this.options.pythonCommand ?? this.options.env?.VISIONFORGE_PYTHON ?? "python";
    let unavailableBeforeReady = false;

    this.child = spawnProcess(pythonCommand, ["-m", "visionforge_app.api"], {
      env: {
        ...process.env,
        ...this.options.env,
        VISIONFORGE_API_PORT: String(port),
        VISIONFORGE_PROJECT: this.options.projectPath,
      },
      stdio: ["ignore", "pipe", "pipe"],
      windowsHide: true,
    });

    this.child.once("exit", () => {
      if (this.apiBaseUrl === null) {
        unavailableBeforeReady = true;
      }
      this.child = null;
    });
    this.child.once("error", (error) => {
      if (this.apiBaseUrl === null) {
        unavailableBeforeReady = true;
      }
      console.error("[visionforge-api] failed to spawn sidecar:", error);
    });
    this.child.stderr?.on("data", (chunk: Buffer) => {
      console.error(`[visionforge-api] ${chunk.toString().trimEnd()}`);
    });

    try {
      await this.waitForHealth(baseUrl, () => unavailableBeforeReady);
      this.apiBaseUrl = baseUrl;
      return baseUrl;
    } catch (error) {
      this.stop();
      throw new SidecarStartError("VisionForge API sidecar failed to become healthy.", {
        cause: error,
      });
    }
  }

  stop(): void {
    const child = this.child;
    this.child = null;
    this.apiBaseUrl = null;
    if (child !== null && !child.killed) {
      child.kill();
    }
  }

  private async waitForHealth(baseUrl: string, hasExited: () => boolean): Promise<void> {
    const fetchHealth = this.options.fetchHealth ?? fetch;
    const timeoutMs = this.options.healthTimeoutMs ?? DEFAULT_SIDECAR_HEALTH_TIMEOUT_MS;
    const pollIntervalMs = this.options.pollIntervalMs ?? DEFAULT_SIDECAR_POLL_INTERVAL_MS;
    const deadline = Date.now() + timeoutMs;
    let lastError: unknown;

    while (Date.now() <= deadline) {
      if (hasExited()) {
        throw new Error("Sidecar process exited before health check passed.");
      }

      try {
        const response = await fetchHealth(`${baseUrl}/health`);
        if (response.ok && isHealthyPayload(await response.json())) {
          return;
        }
      } catch (error) {
        lastError = error;
      }

      await delay(pollIntervalMs);
    }

    throw new Error("Timed out waiting for sidecar health check.", { cause: lastError });
  }
}
