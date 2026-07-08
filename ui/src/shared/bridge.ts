export interface DesktopBridge {
  pickDirectory(): Promise<string | null>;
  showNotification(title: string, body: string): void;
  openExternal(url: string): Promise<void>;
  getAppVersion(): Promise<string>;
  getPlatform(): Promise<"win32" | "darwin" | "linux">;
  getApiBaseUrl(): Promise<string>;
}
