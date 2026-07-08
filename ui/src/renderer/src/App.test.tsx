import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { DesktopBridge } from "../../shared/bridge";
import App from "./App";
import { SAMPLE_MEDIA } from "./data/mediaStub";

describe("App", () => {
  const bridge: DesktopBridge = {
    pickDirectory: vi.fn(),
    showNotification: vi.fn(),
    openExternal: vi.fn(),
    getAppVersion: vi.fn(),
    getPlatform: vi.fn(),
  };

  beforeEach(() => {
    vi.mocked(bridge.getAppVersion).mockResolvedValue("0.1.0");

    Object.defineProperty(window, "bridge", {
      configurable: true,
      value: bridge,
    });
  });

  afterEach(() => {
    cleanup();
  });

  it("renders the shell stations and app version from DesktopBridge", async () => {
    render(<App />);

    for (const label of ["看懂", "整理", "鑄造", "應用"]) {
      expect(screen.getByRole("button", { name: new RegExp(label) })).toBeInTheDocument();
    }
    expect(await screen.findByText("v0.1.0")).toBeInTheDocument();
    expect(bridge.getAppVersion).toHaveBeenCalledOnce();
  });

  it("switches to construction panels for later stations", () => {
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: /鑄造/ }));
    expect(screen.getByRole("heading", { name: "鑄造施工中" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /應用/ }));
    expect(screen.getByRole("heading", { name: "應用施工中" })).toBeInTheDocument();
  });

  it("renders the understand drop zone and typed media grid", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "看懂" })).toBeInTheDocument();
    expect(screen.getByText("待匯入（尚未接後端）")).toBeInTheDocument();

    const grid = screen.getByRole("list", { name: "媒體縮圖網格" });
    expect(within(grid).getAllByRole("listitem")).toHaveLength(SAMPLE_MEDIA.length);
    for (const item of SAMPLE_MEDIA) {
      expect(screen.getByText(item.format)).toBeInTheDocument();
      expect(screen.getByText(`${item.width_px}×${item.height_px}`)).toBeInTheDocument();
    }
  });

  it("lists dropped file names without invoking desktop bridge methods", () => {
    render(<App />);

    fireEvent.drop(screen.getByTestId("drop-zone"), {
      dataTransfer: {
        files: [new File(["image"], "panel-a.jpg", { type: "image/jpeg" })],
      },
    });

    expect(screen.getByText("panel-a.jpg")).toBeInTheDocument();
    expect(bridge.pickDirectory).not.toHaveBeenCalled();
    expect(bridge.openExternal).not.toHaveBeenCalled();
  });
});
