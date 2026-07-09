import { EventEmitter } from "node:events";
import type { ChildProcess } from "node:child_process";
import { describe, expect, it, vi } from "vitest";
import {
  SidecarManager,
  SidecarStartError,
  pickFreeLoopbackPort,
  resolveProviderConfigPath,
  toApiBaseUrl,
} from "./sidecar";

class FakeChildProcess extends EventEmitter {
  killed = false;
  stderr = new EventEmitter();

  kill(): boolean {
    this.killed = true;
    this.emit("exit", null, "SIGTERM");
    return true;
  }
}

const healthyResponse = () =>
  new Response(JSON.stringify({ status: "ok" }), {
    headers: { "content-type": "application/json" },
    status: 200,
  });

describe("sidecar", () => {
  it("allocates a legal loopback port", async () => {
    const port = await pickFreeLoopbackPort();

    expect(Number.isInteger(port)).toBe(true);
    expect(port).toBeGreaterThan(0);
    expect(port).toBeLessThan(65_536);
  });

  it("starts the Python sidecar and exposes the API base URL after health passes", async () => {
    const child = new FakeChildProcess();
    const spawnProcess = vi.fn(() => child as unknown as ChildProcess);
    const fetchHealth = vi.fn(async () => healthyResponse());
    const manager = new SidecarManager({
      env: { VISIONFORGE_PYTHON: "python-test" },
      fetchHealth,
      pickPort: async () => 45_123,
      projectPath: "C:/tmp/visionforge-project",
      spawnProcess,
    });

    await expect(manager.start()).resolves.toBe("http://127.0.0.1:45123");
    expect(manager.getApiBaseUrl()).toBe("http://127.0.0.1:45123");
    expect(fetchHealth).toHaveBeenCalledWith("http://127.0.0.1:45123/health");
    expect(spawnProcess).toHaveBeenCalledWith(
      "python-test",
      ["-m", "visionforge_app.api"],
      expect.objectContaining({
        env: expect.objectContaining({
          VISIONFORGE_API_PORT: "45123",
          VISIONFORGE_PARENT_PID: String(process.pid),
          VISIONFORGE_PROJECT: "C:/tmp/visionforge-project",
        }),
        windowsHide: true,
      }),
    );
  });

  it("uses VISIONFORGE_PYTHON from the current process environment", async () => {
    const previousPython = process.env.VISIONFORGE_PYTHON;
    process.env.VISIONFORGE_PYTHON = "python-from-process-env";

    try {
      const child = new FakeChildProcess();
      const spawnProcess = vi.fn(() => child as unknown as ChildProcess);
      const manager = new SidecarManager({
        fetchHealth: vi.fn(async () => healthyResponse()),
        pickPort: async () => 45_125,
        projectPath: "C:/tmp/visionforge-project",
        spawnProcess,
      });

      await expect(manager.start()).resolves.toBe("http://127.0.0.1:45125");
      expect(spawnProcess).toHaveBeenCalledWith(
        "python-from-process-env",
        ["-m", "visionforge_app.api"],
        expect.objectContaining({
          env: expect.objectContaining({
            VISIONFORGE_PYTHON: "python-from-process-env",
          }),
        }),
      );
    } finally {
      if (previousPython === undefined) {
        delete process.env.VISIONFORGE_PYTHON;
      } else {
        process.env.VISIONFORGE_PYTHON = previousPython;
      }
    }
  });

  it("terminates the child process when health never becomes ready", async () => {
    const child = new FakeChildProcess();
    const manager = new SidecarManager({
      fetchHealth: vi.fn(async () => new Response(JSON.stringify({ status: "starting" }))),
      healthTimeoutMs: 1,
      pickPort: async () => 45_124,
      pollIntervalMs: 1,
      projectPath: "C:/tmp/visionforge-project",
      spawnProcess: vi.fn(() => child as unknown as ChildProcess),
    });

    await expect(manager.start()).rejects.toBeInstanceOf(SidecarStartError);
    expect(child.killed).toBe(true);
  });

  it("formats only loopback API base URLs", () => {
    expect(toApiBaseUrl(8765)).toBe("http://127.0.0.1:8765");
  });

  it("keeps an explicit provider config path from the environment", () => {
    expect(
      resolveProviderConfigPath(
        "C:/tmp/project",
        { VISIONFORGE_PROVIDER_CONFIG: "C:/safe/provider-config.json" },
        "C:/repo/ui",
        () => false,
      ),
    ).toBe("C:/safe/provider-config.json");
  });

  it("finds a provider config in the dev repo root when the project is elsewhere", () => {
    const found = resolveProviderConfigPath(
      "C:/user-data/dev-project",
      {},
      "C:/repo/ui",
      (path) => path.replaceAll("\\", "/") === "C:/repo/provider-config.json",
    );

    expect(found?.replaceAll("\\", "/")).toBe("C:/repo/provider-config.json");
  });
});
