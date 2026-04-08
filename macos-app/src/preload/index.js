import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('electronAPI', {
  onSidecarReady:  (cb)    => ipcRenderer.on('sidecar-ready', (_, data) => cb(data)),
  onSidecarError:  (cb)    => ipcRenderer.on('sidecar-error', (_, data) => cb(data)),
  getPort:         ()      => ipcRenderer.invoke('get-port'),
  openExternal:    (url)   => ipcRenderer.invoke('open-external', url),
  updateTray:      (data)  => ipcRenderer.send('update-tray', data),
})
