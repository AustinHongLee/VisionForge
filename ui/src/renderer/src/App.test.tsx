import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { DesktopBridge } from "../../shared/bridge";
import type { Claim, MediaRecord } from "../../shared/contracts.generated";
import App from "./App";

const API_BASE = "http://127.0.0.1:8765";
const TASK_ID = "0000000000000000000000000A";
const CONCEPT_ID = "0000000000000000000000000B";

const mediaA: MediaRecord = {
  byte_size: 582144,
  exif_normalized: true,
  format: "jpeg",
  height_px: 1080,
  imported_at: "2026-07-08T02:15:00Z",
  media_hash: "49ab860f370463b727f21321f4149d9a1cced7ea27dd0b116bd73824aaa18495",
  schema_version: "1.0",
  source: { detail: "panel-a.jpg", kind: "file" },
  width_px: 1920,
};

const mediaB: MediaRecord = {
  byte_size: 241008,
  exif_normalized: true,
  format: "png",
  height_px: 960,
  imported_at: "2026-07-08T02:17:00Z",
  media_hash: "308459369f46f29cb2c17ecf1a9ddec5db0252a2165978004ec72fe065fc6104",
  schema_version: "1.0",
  source: { detail: "panel-b.png", kind: "file" },
  width_px: 1280,
};

const teacherClaim: Claim = {
  assertion: "presence",
  claim_id: "0000000000000000000000000C",
  concept: { raw_text: "Gate Valve" },
  confidence: { raw: 0.8, reliability: "none" },
  geometry: { type: "bbox", x1: 0.1, x2: 0.5, y1: 0.2, y2: 0.6 },
};

const page = (items: MediaRecord[]) => ({
  has_more: false,
  items,
  limit: 100,
  offset: 0,
  total: items.length,
});

const jsonResponse = (body: unknown, init: ResponseInit = {}) =>
  new Response(JSON.stringify(body), {
    headers: { "content-type": "application/json" },
    status: 200,
    ...init,
  });

describe("App", () => {
  const bridge: DesktopBridge = {
    getApiBaseUrl: vi.fn(),
    getAppVersion: vi.fn(),
    getPlatform: vi.fn(),
    openExternal: vi.fn(),
    pickDirectory: vi.fn(),
    showNotification: vi.fn(),
  };

  const fetchMock = vi.fn<(input: RequestInfo | URL, init?: RequestInit) => Promise<Response>>();

  beforeEach(() => {
    vi.mocked(bridge.getApiBaseUrl).mockResolvedValue(API_BASE);
    vi.mocked(bridge.getAppVersion).mockResolvedValue("0.1.0");
    fetchMock.mockReset();
    globalThis.fetch = fetchMock;
    URL.createObjectURL = vi.fn(() => "blob:preview");
    URL.revokeObjectURL = vi.fn();
    Object.defineProperty(window, "bridge", { configurable: true, value: bridge });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  const emptyApi = async (input: RequestInfo | URL): Promise<Response> => {
    const path = new URL(String(input)).pathname;
    return path === "/tasks" ? jsonResponse([]) : jsonResponse(page([]));
  };

  it("renders the R3 stations and app version", async () => {
    fetchMock.mockImplementation(emptyApi);

    render(<App />);

    for (const label of ["教學", "鑄造", "版本", "應用"]) {
      expect(screen.getByRole("button", { name: new RegExp(label) })).toBeInTheDocument();
    }
    expect(await screen.findByText("v0.1.0")).toBeInTheDocument();
  });

  it("opens the portable capability release station", () => {
    fetchMock.mockImplementation(emptyApi);
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: /版本/ }));
    expect(screen.getByRole("heading", { name: "把能力帶走，不依賴 Studio" })).toBeInTheDocument();
  });

  it("loads media and renders thumbnail images", async () => {
    fetchMock.mockImplementation(async (input) => {
      const path = new URL(String(input)).pathname;
      return path === "/tasks" ? jsonResponse([]) : jsonResponse(page([mediaA, mediaB]));
    });

    render(<App />);

    const grid = await screen.findByRole("list", { name: "媒體縮圖網格" });
    expect(within(grid).getAllByRole("img")).toHaveLength(2);
    expect(within(grid).getByAltText("panel-a.jpg")).toHaveAttribute(
      "src",
      `${API_BASE}/media/${mediaA.media_hash}/thumbnail`,
    );
  });

  it("imports dropped files and reloads the media list", async () => {
    let items: MediaRecord[] = [];
    fetchMock.mockImplementation(async (input, init) => {
      const path = new URL(String(input)).pathname;
      if (path === "/tasks") return jsonResponse([]);
      if (path === "/import") {
        items = [mediaA];
        expect(init?.body).toBeInstanceOf(FormData);
        return jsonResponse({ deduplicated: false, media_hash: mediaA.media_hash, record: mediaA });
      }
      return jsonResponse(page(items));
    });

    render(<App />);
    await screen.findByText("尚無匯入影像");
    fireEvent.drop(screen.getByTestId("drop-zone"), {
      dataTransfer: { files: [new File(["image"], "panel-a.jpg", { type: "image/jpeg" })] },
    });

    expect(await screen.findByText("panel-a.jpg")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE}/import`,
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("runs the first-forge user flow without a technical reviewer step", async () => {
    const task = {
      created_at: "2026-07-13T00:00:00Z",
      kind: "detect",
      name: "閥件偵測",
      task_id: TASK_ID,
    };
    const concept = {
      aliases: [],
      concept_id: CONCEPT_ID,
      created_at: "2026-07-13T00:00:01Z",
      display_name: "Gate Valve",
      task_id: TASK_ID,
    };
    let tasks: unknown[] = [];
    let concepts: unknown[] = [];
    let assigned = false;
    let claims: Claim[] = [];
    let annotations: unknown[] = [];
    let coverageState = "unverified";

    fetchMock.mockImplementation(async (input, init) => {
      const url = new URL(String(input));
      const path = url.pathname;
      const method = init?.method ?? "GET";
      if (path === "/media") return jsonResponse(page([mediaA]));
      if (path === "/tasks" && method === "GET") return jsonResponse(tasks);
      if (path === "/tasks" && method === "POST") {
        tasks = [task];
        return jsonResponse(task);
      }
      if (path === `/tasks/${TASK_ID}/concepts` && method === "GET") {
        return jsonResponse(concepts);
      }
      if (path === `/tasks/${TASK_ID}/concepts` && method === "POST") {
        concepts = [concept];
        return jsonResponse(concept);
      }
      if (path.endsWith("/teaching")) {
        if (!assigned) return jsonResponse({ detail: { error: "scope_not_found" } }, { status: 404 });
        return jsonResponse({
          annotations,
          assignment: {
            assigned_at: "2026-07-13T00:00:02Z",
            media_hash: mediaA.media_hash,
            source_group_id: mediaA.media_hash,
            task_id: TASK_ID,
          },
          concepts,
          coverage: [
            {
              concept_id: CONCEPT_ID,
              media_hash: mediaA.media_hash,
              state: coverageState,
              task_id: TASK_ID,
            },
          ],
          task,
          teacher_claims: claims,
        });
      }
      if (path.includes(`/tasks/${TASK_ID}/media/`) && method === "POST") {
        assigned = true;
        return jsonResponse({ media_hash: mediaA.media_hash, task_id: TASK_ID });
      }
      if (path === `/tasks/${TASK_ID}/teach`) {
        assigned = true;
        claims = [teacherClaim];
        return jsonResponse({ claims, run_id: "0000000000000000000000000D" });
      }
      if (path === "/annotations" && method === "POST") {
        const body = JSON.parse(String(init?.body)) as { source_claim_ref: string };
        expect(body.source_claim_ref).toBe(teacherClaim.claim_id);
        annotations = [
          {
            annotation_id: "0000000000000000000000000E",
            bbox: teacherClaim.geometry,
            concept_id: CONCEPT_ID,
            created_at: "2026-07-13T00:00:03Z",
            created_by: "local-user",
            media_hash: mediaA.media_hash,
            revision_id: "0000000000000000000000000F",
            source: "teacher_accepted",
            source_claim_ref: teacherClaim.claim_id,
            task_id: TASK_ID,
          },
        ];
        return jsonResponse(annotations[0]);
      }
      if (path === "/coverage" && method === "PUT") {
        coverageState = "verified_complete";
        return jsonResponse({ state: coverageState });
      }
      throw new Error(`Unexpected request: ${method} ${path}`);
    });

    render(<App />);
    await screen.findByAltText("panel-a.jpg");
    fireEvent.change(screen.getByLabelText("新任務名稱"), { target: { value: "閥件偵測" } });
    fireEvent.click(screen.getByRole("button", { name: "建立任務" }));

    await waitFor(() => expect(screen.getByLabelText("能力任務")).toHaveValue(TASK_ID));
    fireEvent.change(screen.getByLabelText("要教的物件"), { target: { value: "Gate Valve" } });
    fireEvent.click(screen.getByRole("button", { name: "新增物件" }));
    expect(await screen.findByText("Gate Valve")).toBeInTheDocument();

    fireEvent.click(await screen.findByRole("button", { name: "加入任務" }));
    fireEvent.click(await screen.findByRole("button", { name: "請教師框選" }));
    fireEvent.click(await screen.findByRole("button", { name: "接受這個框" }));

    expect(await screen.findByTestId("annotation-box")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "框完了" }));
    expect(await screen.findByText("verified_complete")).toBeInTheDocument();
    expect(screen.queryByText("批准")).not.toBeInTheDocument();
  });

  it("freezes a dataset and starts a child-process training attempt from Distill", async () => {
    const task = {
      created_at: "2026-07-13T00:00:00Z",
      kind: "detect",
      name: "閥件偵測",
      task_id: TASK_ID,
    };
    const dataset = {
      class_map: [{ class_index: 0, concept_id: CONCEPT_ID, display_name: "Gate Valve" }],
      concept_ids: [CONCEPT_ID],
      created_at: "2026-07-13T00:00:00Z",
      dataset_version_id: "0000000000000000000000000D",
      items: [
        { annotations: [], coverage: [], media_hash: "1".repeat(64), source_group_id: "a", split: "train" },
        { annotations: [], coverage: [], media_hash: "2".repeat(64), source_group_id: "b", split: "validation" },
      ],
      task_id: TASK_ID,
      version_number: 1,
    };
    let freezeCalls = 0;
    let trainingCalls = 0;
    fetchMock.mockImplementation(async (input, init) => {
      const path = new URL(String(input)).pathname;
      const method = init?.method ?? "GET";
      if (path === "/media") return jsonResponse(page([]));
      if (path === "/tasks") return jsonResponse([task]);
      if (path.endsWith("/readiness")) {
        return jsonResponse({ blockers: [], warnings: [{ code: "few", message: "樣本偏少" }] });
      }
      if (path.endsWith("/datasets") && method === "GET") return jsonResponse([dataset]);
      if (path.endsWith("/datasets/freeze")) {
        freezeCalls += 1;
        return jsonResponse({ readiness: { blockers: [], warnings: [] }, version: dataset });
      }
      if (path.endsWith("/training") && method === "GET") return jsonResponse([]);
      if (path.endsWith("/artifacts")) return jsonResponse([]);
      if (path === "/training" && method === "POST") {
        trainingCalls += 1;
        return jsonResponse({ training_run_id: "0000000000000000000000000E" });
      }
      throw new Error(`Unexpected ${method} ${path}`);
    });

    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: /鑄造/ }));
    expect(await screen.findByText("樣本偏少")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "凍結新資料版本" }));
    await waitFor(() => expect(freezeCalls).toBe(1));
    fireEvent.click(await screen.findByRole("button", { name: "開始鑄造" }));
    await waitFor(() => expect(trainingCalls).toBe(1));
  });

  it("runs an immutable ModelArtifact against a new unimported image", async () => {
    const task = {
      created_at: "2026-07-13T00:00:00Z",
      kind: "detect",
      name: "閥件偵測",
      task_id: TASK_ID,
    };
    const artifactId = "0000000000000000000000000F";
    const artifact = {
      artifact_hash: "a".repeat(64),
      artifact_id: artifactId,
      class_map: [{ class_index: 0, concept_id: CONCEPT_ID, display_name: "Gate Valve" }],
      confidence_threshold: 0.35,
      created_at: "2026-07-13T00:00:00Z",
      dataset_version_id: "0000000000000000000000000D",
      input_size: 256,
      relative_path: "artifacts/model.pt",
      task_id: TASK_ID,
      training_run_id: "0000000000000000000000000E",
    };
    fetchMock.mockImplementation(async (input, init) => {
      const path = new URL(String(input)).pathname;
      if (path === "/media") return jsonResponse(page([]));
      if (path === "/tasks") return jsonResponse([task]);
      if (path.endsWith("/artifacts") && (init?.method ?? "GET") === "GET") {
        return jsonResponse([artifact]);
      }
      if (path === `/artifacts/${artifactId}/infer`) {
        expect(init?.body).toBeInstanceOf(FormData);
        return jsonResponse({
          artifact_id: artifactId,
          predictions: [
            {
              bbox: { type: "bbox", x1: 0.1, x2: 0.5, y1: 0.2, y2: 0.6 },
              concept_id: CONCEPT_ID,
              confidence: 0.88,
              display_name: "Gate Valve",
            },
          ],
        });
      }
      throw new Error(`Unexpected request ${path}`);
    });

    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: /應用/ }));
    const input = await screen.findByLabelText("選擇新圖片");
    fireEvent.change(input, {
      target: { files: [new File(["image"], "new.png", { type: "image/png" })] },
    });
    fireEvent.click(screen.getByRole("button", { name: "執行本地模型" }));

    expect(await screen.findByText("Gate Valve 88%")).toBeInTheDocument();
  });

  it("publishes and exposes a portable CapabilityRelease archive", async () => {
    const task = {
      created_at: "2026-07-13T00:00:00Z",
      kind: "detect",
      name: "閥件偵測",
      task_id: TASK_ID,
    };
    const artifactId = "0000000000000000000000000F";
    const artifact = {
      artifact_hash: "a".repeat(64),
      artifact_id: artifactId,
      class_map: [{ class_index: 0, concept_id: CONCEPT_ID, display_name: "Gate Valve" }],
      confidence_threshold: 0.35,
      created_at: "2026-07-13T00:00:00Z",
      dataset_version_id: "0000000000000000000000000D",
      input_size: 256,
      relative_path: "artifacts/model.pt",
      task_id: TASK_ID,
      training_run_id: "0000000000000000000000000E",
    };
    const release = {
      archive_hash: "b".repeat(64),
      artifact_ids: [artifactId],
      created_at: "2026-07-13T00:00:00Z",
      manifest_hash: "c".repeat(64),
      relative_path: "releases/v1.zip",
      release_id: "0000000000000000000000000G",
      task_id: TASK_ID,
      version_number: 1,
    };
    let releases: unknown[] = [];
    fetchMock.mockImplementation(async (input, init) => {
      const path = new URL(String(input)).pathname;
      const method = init?.method ?? "GET";
      if (path === "/media") return jsonResponse(page([]));
      if (path === "/tasks") return jsonResponse([task]);
      if (path.endsWith("/artifacts")) return jsonResponse([artifact]);
      if (path.endsWith("/releases") && method === "GET") return jsonResponse(releases);
      if (path === "/releases" && method === "POST") {
        releases = [release];
        return jsonResponse(release);
      }
      throw new Error(`Unexpected request ${method} ${path}`);
    });

    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: /版本/ }));
    fireEvent.click(await screen.findByRole("button", { name: "發布下一個能力版本" }));

    const link = await screen.findByRole("link", { name: "儲存 zip" });
    expect(screen.getByText("CapabilityRelease v1")).toBeInTheDocument();
    expect(link).toHaveAttribute(
      "href",
      `${API_BASE}/releases/${release.release_id}/archive`,
    );
  });

  it("shows an error state when the API base URL is not ready", async () => {
    vi.mocked(bridge.getApiBaseUrl).mockRejectedValue(new Error("sidecar unavailable"));
    render(<App />);

    expect(await screen.findByRole("alert")).toHaveTextContent("sidecar unavailable");
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
