import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('electronAPI', {
  // Sidecar lifecycle
  onSidecarReady:      (cb) => ipcRenderer.on('sidecar-ready', (_, data) => cb(data)),
  onSidecarError:      (cb) => ipcRenderer.on('sidecar-error', (_, data) => cb(data)),
  getPort:             ()   => ipcRenderer.invoke('get-port'),
  openExternal:        (url) => ipcRenderer.invoke('open-external', url),
  updateTray:          (data) => ipcRenderer.send('update-tray', data),

  // Setup / bootstrap
  onSetupProgress:     (cb) => ipcRenderer.on('setup-progress', (_, data) => cb(data)),
  onSetupPythonMissing:(cb) => ipcRenderer.on('setup-python-missing', (_, data) => cb(data)),
  retrySetup:          ()   => ipcRenderer.invoke('retry-setup'),
  resetVenv:           ()   => ipcRenderer.invoke('reset-venv'),
})
