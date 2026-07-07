import { app, BrowserWindow, dialog, ipcMain, Notification, shell } from "electron";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import { BRIDGE_CHANNELS } from "../shared/ipcChannels";
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

const registerBridgeHandlers = (): void => {
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

app.whenReady().then(() => {
  registerBridgeHandlers();
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
