'use strict'

const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  // Sidecar events from main → renderer
  onSidecarReady: (cb) => ipcRenderer.on('sidecar-ready', (_, data) => cb(data)),
  onSidecarError: (cb) => ipcRenderer.on('sidecar-error', (_, data) => cb(data)),
})
