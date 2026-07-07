import { app, BrowserWindow, dialog, ipcMain, Notification, shell } from "electron";
import { join } from "node:path";
import { BRIDGE_CHANNELS } from "../shared/ipcChannels";

type DesktopPlatform = "win32" | "darwin" | "linux";

const getDesktopPlatform = (): DesktopPlatform => {
  if (process.platform === "win32" || process.platform === "darwin" || process.platform === "linux") {
    return process.platform;
  }

  return "linux";
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
    await shell.openExternal(url);
  });

  ipcMain.handle(BRIDGE_CHANNELS.getAppVersion, () => app.getVersion());
  ipcMain.handle(BRIDGE_CHANNELS.getPlatform, () => getDesktopPlatform());
};

const createWindow = (): void => {
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

  if (process.env.ELECTRON_RENDERER_URL) {
    void mainWindow.loadURL(process.env.ELECTRON_RENDERER_URL);
    return;
  }

  void mainWindow.loadFile(join(__dirname, "../renderer/index.html"));
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
