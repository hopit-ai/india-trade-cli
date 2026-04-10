// Electron API stubs for web mode
// When running as a web app (not inside Electron), provide no-op implementations
// so the React app doesn't crash on missing IPC bridges.
if (!window.electronAPI) {
  window.electronAPI = {
    getPort: () => Promise.resolve(null),
    openExternal: (url) => window.open(url, '_blank'),
    updateTray: () => {},
    onSidecarReady: (cb) => {},
    onSidecarError: (cb) => {},
    onSetupProgress: (cb) => {},
    onSetupPythonMissing: (cb) => {},
    retrySetup: () => Promise.resolve(),
    resetVenv: () => Promise.resolve(),
  }
}
window.__INDIA_TRADE_WEB__ = true
