import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { DesktopBridge } from "../../shared/bridge";
import App from "./App";

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

  it("renders the app version from DesktopBridge", async () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "VisionForge — 施工中" })).toBeInTheDocument();
    expect(await screen.findByText("v0.1.0")).toBeInTheDocument();
    expect(bridge.getAppVersion).toHaveBeenCalledOnce();
  });
});
