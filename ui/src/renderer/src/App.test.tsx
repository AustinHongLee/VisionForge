import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { DesktopBridge } from "../../shared/bridge";
import type { Claim, MediaRecord } from "../../shared/contracts.generated";
import App from "./App";

const API_BASE = "http://127.0.0.1:8765";

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

const claim = (rawText: string, claimId: string, raw: number): Claim => ({
  assertion: "presence",
  claim_id: claimId,
  concept: { raw_text: rawText },
  confidence: { raw, reliability: "none" },
  geometry: { type: "bbox", x1: 0.1, x2: 0.5, y1: 0.2, y2: 0.6 },
});

const pendingItem = (rawText: string, claimId: string, raw: number, media = mediaA) => ({
  claim: claim(rawText, claimId, raw),
  media_hash: media.media_hash,
  run_ref: "0000000000000000000000000A",
});

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

    Object.defineProperty(window, "bridge", {
      configurable: true,
      value: bridge,
    });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("renders the shell stations and app version from DesktopBridge", async () => {
    fetchMock.mockResolvedValue(jsonResponse(page([])));

    render(<App />);

    for (const label of ["看懂", "整理", "鑄造", "應用"]) {
      expect(screen.getByRole("button", { name: new RegExp(label) })).toBeInTheDocument();
    }
    expect(await screen.findByText("v0.1.0")).toBeInTheDocument();
    expect(bridge.getAppVersion).toHaveBeenCalledOnce();
  });

  it("switches to construction panels for later stations", () => {
    fetchMock.mockResolvedValue(jsonResponse(page([])));

    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: /鑄造/ }));
    expect(screen.getByRole("heading", { name: "鑄造施工中" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /應用/ }));
    expect(screen.getByRole("heading", { name: "應用施工中" })).toBeInTheDocument();
  });

  it("loads media from the API and renders thumbnail images", async () => {
    fetchMock.mockResolvedValue(jsonResponse(page([mediaA, mediaB])));

    render(<App />);

    const grid = await screen.findByRole("list", { name: "媒體縮圖網格" });
    expect(within(grid).getAllByRole("img")).toHaveLength(2);
    expect(within(grid).getByAltText("panel-a.jpg")).toHaveAttribute(
      "src",
      `${API_BASE}/media/${mediaA.media_hash}/thumbnail`,
    );
    expect(fetchMock).toHaveBeenCalledWith(`${API_BASE}/media?limit=100&offset=0`);
  });

  it("imports dropped files and reloads the media list", async () => {
    let items: MediaRecord[] = [];
    fetchMock.mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith("/import")) {
        items = [mediaA];
        expect(init?.method).toBe("POST");
        expect(init?.body).toBeInstanceOf(FormData);
        return jsonResponse({ deduplicated: false, media_hash: mediaA.media_hash, record: mediaA });
      }
      return jsonResponse(page(items));
    });

    render(<App />);
    await screen.findByText("尚無匯入影像");

    const file = new File(["image"], "panel-a.jpg", { type: "image/jpeg" });
    fireEvent.drop(screen.getByTestId("drop-zone"), {
      dataTransfer: { files: [file] },
    });

    expect(await screen.findByText("panel-a.jpg")).toBeInTheDocument();
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        `${API_BASE}/import`,
        expect.objectContaining({ method: "POST" }),
      );
      expect(fetchMock).toHaveBeenCalledTimes(3);
    });
  });

  it("selects a thumbnail, sends infer concepts, and renders returned boxes", async () => {
    fetchMock.mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith("/infer")) {
        expect(init?.method).toBe("POST");
        expect(JSON.parse(String(init?.body))).toEqual({
          concepts: [{ raw_text: "bolt" }, { raw_text: "crack" }],
          media_hash: mediaA.media_hash,
        });
        return jsonResponse({
          claims: [
            claim("bolt", "00000000000000000000000001", 0.73),
            claim("crack", "00000000000000000000000002", 0.61),
          ],
          provider_id: "fixture",
        });
      }
      return jsonResponse(page([mediaA]));
    });

    render(<App />);
    const grid = await screen.findByRole("list", { name: "媒體縮圖網格" });
    fireEvent.click(within(grid).getByRole("img", { name: "panel-a.jpg" }));
    fireEvent.change(screen.getByLabelText("概念"), { target: { value: "bolt, crack" } });
    fireEvent.click(screen.getByRole("button", { name: "偵測" }));

    expect(await screen.findByLabelText("偵測框 bolt")).toBeInTheDocument();
    expect(screen.getByLabelText("偵測框 crack")).toBeInTheDocument();
    expect(screen.getAllByTestId("claim-box")).toHaveLength(2);
    for (const box of screen.getAllByTestId("claim-box")) {
      expect(box).toHaveClass("reliability-none");
    }
  });

  it("shows an error state when the API base URL is not ready", async () => {
    vi.mocked(bridge.getApiBaseUrl).mockRejectedValue(new Error("sidecar unavailable"));

    render(<App />);

    expect(await screen.findByRole("alert")).toHaveTextContent("sidecar unavailable");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("renders grouped review cards with thumbnail overlays", async () => {
    const pending = [
      pendingItem("bolt", "00000000000000000000000001", 0.73),
      pendingItem("bolt", "00000000000000000000000002", 0.61),
      pendingItem("crack", "00000000000000000000000003", 0.44, mediaB),
    ];
    fetchMock.mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/review/pending")) {
        return jsonResponse(pending);
      }
      return jsonResponse(page([]));
    });

    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: /整理/ }));

    expect(await screen.findByRole("region", { name: "概念 bolt" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "概念 crack" })).toBeInTheDocument();
    expect(screen.getByText("73%")).toBeInTheDocument();
    expect(screen.getByText("44%")).toBeInTheDocument();
    expect(screen.getAllByTestId("claim-box")).toHaveLength(3);
    expect(screen.getAllByLabelText("偵測框 bolt")[0]).toHaveStyle({
      height: "40%",
      left: "10%",
      top: "20%",
      width: "40%",
    });
    expect(screen.getAllByAltText("bolt 待審縮圖")[0]).toHaveAttribute(
      "src",
      `${API_BASE}/media/${mediaA.media_hash}/thumbnail`,
    );
  });

  it("approves a pending claim and reloads the review queue", async () => {
    let pending = [pendingItem("bolt", "00000000000000000000000001", 0.73)];
    fetchMock.mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith("/review/pending")) {
        return jsonResponse(pending);
      }
      if (url.endsWith("/review/approve")) {
        pending = [];
        expect(init?.method).toBe("POST");
        expect(JSON.parse(String(init?.body))).toEqual({
          claim_id: "00000000000000000000000001",
          reviewer: "local-user",
        });
        return jsonResponse({ label_id: "0000000000000000000000000B" });
      }
      return jsonResponse(page([]));
    });

    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: /整理/ }));
    fireEvent.click(await screen.findByRole("button", { name: "批准" }));

    expect(await screen.findByRole("heading", { name: "尚無待審 Claim" })).toBeInTheDocument();
  });

  it("rejects a pending claim and reloads the review queue", async () => {
    let pending = [pendingItem("crack", "00000000000000000000000003", 0.44)];
    fetchMock.mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith("/review/pending")) {
        return jsonResponse(pending);
      }
      if (url.endsWith("/review/reject")) {
        pending = [];
        expect(init?.method).toBe("POST");
        expect(JSON.parse(String(init?.body))).toEqual({
          claim_id: "00000000000000000000000003",
          reviewer: "local-user",
        });
        return jsonResponse({ event_id: "0000000000000000000000000C", to_status: "rejected" });
      }
      return jsonResponse(page([]));
    });

    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: /整理/ }));
    fireEvent.click(await screen.findByRole("button", { name: "否決" }));

    expect(await screen.findByRole("heading", { name: "尚無待審 Claim" })).toBeInTheDocument();
  });

  it("shows an empty recalibration result for 204 responses", async () => {
    fetchMock.mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith("/review/pending")) {
        return jsonResponse([]);
      }
      if (url.endsWith("/recalibrate")) {
        expect(init?.method).toBe("POST");
        return new Response(null, { status: 204 });
      }
      return jsonResponse(page([]));
    });

    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: /整理/ }));
    fireEvent.click(await screen.findByRole("button", { name: "重新校準" }));

    expect(await screen.findByText("尚無已審結果")).toBeInTheDocument();
  });

  it("shows a curate error state when the API base URL is not ready", async () => {
    fetchMock.mockResolvedValue(jsonResponse(page([])));
    vi.mocked(bridge.getApiBaseUrl).mockRejectedValue(new Error("sidecar unavailable"));

    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: /整理/ }));

    expect(await screen.findByRole("alert")).toHaveTextContent("sidecar unavailable");
  });
});
