import { contextBridge, ipcRenderer } from "electron";
import type { DesktopBridge } from "../shared/bridge";
import { BRIDGE_CHANNELS } from "../shared/ipcChannels";

const bridge: DesktopBridge = {
  pickDirectory: () => ipcRenderer.invoke(BRIDGE_CHANNELS.pickDirectory),
  showNotification: (title, body) => {
    ipcRenderer.send(BRIDGE_CHANNELS.showNotification, title, body);
  },
  openExternal: (url) => ipcRenderer.invoke(BRIDGE_CHANNELS.openExternal, url),
  getAppVersion: () => ipcRenderer.invoke(BRIDGE_CHANNELS.getAppVersion),
  getPlatform: () => ipcRenderer.invoke(BRIDGE_CHANNELS.getPlatform),
  getApiBaseUrl: () => ipcRenderer.invoke(BRIDGE_CHANNELS.getApiBaseUrl),
};

contextBridge.exposeInMainWorld("bridge", bridge);
