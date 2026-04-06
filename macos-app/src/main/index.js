'use strict'

const { app, BrowserWindow, ipcMain, shell } = require('electron')
const path = require('path')
const { startSidecar, stopSidecar } = require('./sidecar')

let mainWindow = null

// ---------------------------------------------------------------------------
// Window
// ---------------------------------------------------------------------------
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    backgroundColor: '#0d0d0d',
    titleBarStyle: 'hiddenInset',
    trafficLightPosition: { x: 16, y: 18 },
    webPreferences: {
      preload: path.join(__dirname, '../preload/index.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
    show: false,
  })

  // Load Vite dev server in dev, built file in production
  if (process.env.NODE_ENV === 'development' || !app.isPackaged) {
    mainWindow.loadURL('http://localhost:5173')
    mainWindow.webContents.openDevTools({ mode: 'detach' })
  } else {
    mainWindow.loadFile(path.join(__dirname, '../../renderer/index.html'))
  }

  mainWindow.once('ready-to-show', () => {
    mainWindow.show()
    // Start the Python sidecar
    startSidecar(
      (port) => mainWindow?.webContents.send('sidecar-ready', { port }),
      (err)  => mainWindow?.webContents.send('sidecar-error', { message: err }),
    )
  })

  mainWindow.on('closed', () => { mainWindow = null })

  // Open external links in system browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url)
    return { action: 'deny' }
  })
}

// ---------------------------------------------------------------------------
// App lifecycle
// ---------------------------------------------------------------------------
app.whenReady().then(createWindow)

app.on('before-quit', stopSidecar)

app.on('window-all-closed', () => {
  stopSidecar()
  app.quit()
})
