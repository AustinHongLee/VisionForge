import { app, BrowserWindow, dialog, ipcMain, Notification, shell } from "electron";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import { BRIDGE_CHANNELS } from "../shared/ipcChannels";
import { SidecarManager } from "./sidecar";
import { isSafeExternalUrl } from "./urlPolicy";

type DesktopPlatform = "win32" | "darwin" | "linux";

const getDesktopPlatform = (): DesktopPlatform => {
  const platform = process.platform;

  if (platform === "win32" || platform === "darwin" || platform === "linux") {
    return platform;
  }

  console.warn(`Unsupported desktop platform "${platform}", falling back to "linux".`);
  return "linux";
};

let sidecarManager: SidecarManager | null = null;
let apiBaseUrl: string | null = null;

const getProjectPath = (): string =>
  process.env.VISIONFORGE_PROJECT ?? join(app.getPath("userData"), "dev-project");

const formatError = (error: unknown): string =>
  error instanceof Error ? error.message : String(error);

const isAllowedAppNavigation = (targetUrl: string, appEntryUrl: string): boolean => {
  try {
    const target = new URL(targetUrl);
    const appEntry = new URL(appEntryUrl);

    if (appEntry.protocol === "file:") {
      return target.protocol === "file:" && target.pathname === appEntry.pathname;
    }

    return target.origin === appEntry.origin;
  } catch {
    return false;
  }
};

const registerBridgeHandlers = (getApiBaseUrl: () => string): void => {
  ipcMain.handle(BRIDGE_CHANNELS.pickDirectory, async () => {
    const result = await dialog.showOpenDialog({
      properties: ["openDirectory"],
    });

    if (result.canceled) {
      return null;
    }

    return result.filePaths[0] ?? null;
  });

  ipcMain.on(BRIDGE_CHANNELS.showNotification, (_event, title: string, body: string) => {
    new Notification({ title, body }).show();
  });

  ipcMain.handle(BRIDGE_CHANNELS.openExternal, async (_event, url: string) => {
    if (!isSafeExternalUrl(url)) {
      console.warn(`Blocked unsafe external URL: ${url}`);
      return;
    }

    await shell.openExternal(url);
  });

  ipcMain.handle(BRIDGE_CHANNELS.getAppVersion, () => app.getVersion());
  ipcMain.handle(BRIDGE_CHANNELS.getPlatform, () => getDesktopPlatform());
  ipcMain.handle(BRIDGE_CHANNELS.getApiBaseUrl, () => getApiBaseUrl());
};

const createWindow = (): void => {
  const rendererHtmlPath = join(__dirname, "../renderer/index.html");
  const rendererEntryUrl =
    process.env.ELECTRON_RENDERER_URL ?? pathToFileURL(rendererHtmlPath).toString();

  const mainWindow = new BrowserWindow({
    width: 1080,
    height: 720,
    minWidth: 720,
    minHeight: 480,
    backgroundColor: "#111318",
    title: "VisionForge",
    webPreferences: {
      preload: join(__dirname, "../preload/index.cjs"),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
    },
  });

  mainWindow.webContents.on("preload-error", (_event, preloadPath, error) => {
    console.error(`Failed to load preload script at ${preloadPath}:`, error);
  });

  mainWindow.webContents.setWindowOpenHandler(() => ({ action: "deny" }));
  mainWindow.webContents.on("will-navigate", (event, url) => {
    if (!isAllowedAppNavigation(url, rendererEntryUrl)) {
      event.preventDefault();
    }
  });

  if (process.env.ELECTRON_RENDERER_URL) {
    void mainWindow.loadURL(rendererEntryUrl);
    return;
  }

  void mainWindow.loadFile(rendererHtmlPath);
};

const focusExistingWindow = (): void => {
  const [window] = BrowserWindow.getAllWindows();
  if (window === undefined) {
    return;
  }
  if (window.isMinimized()) {
    window.restore();
  }
  window.focus();
};

const startSidecar = async (): Promise<string> => {
  sidecarManager = new SidecarManager({
    projectPath: getProjectPath(),
  });
  return sidecarManager.start();
};

const boot = async (): Promise<void> => {
  if (!app.requestSingleInstanceLock()) {
    app.quit();
    return;
  }

  app.on("second-instance", () => {
    focusExistingWindow();
  });

  try {
    apiBaseUrl = await startSidecar();
  } catch (error) {
    dialog.showErrorBox(
      "VisionForge API 啟動失敗",
      `本機 Python sidecar 沒有通過健康檢查：${formatError(error)}`,
    );
    app.quit();
    return;
  }

  registerBridgeHandlers(() => {
    if (apiBaseUrl === null) {
      throw new Error("VisionForge API sidecar is not ready.");
    }
    return apiBaseUrl;
  });
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
};

app.whenReady().then(() => {
  void boot();
});

app.on("will-quit", () => {
  sidecarManager?.stop();
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
