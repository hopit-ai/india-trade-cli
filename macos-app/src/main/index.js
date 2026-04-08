import { app, BrowserWindow, shell, ipcMain, Tray, nativeImage, globalShortcut } from 'electron'
import { join, resolve } from 'path'
import { existsSync, mkdirSync, writeFileSync, readFileSync } from 'fs'
import { homedir } from 'os'
import { spawn } from 'child_process'

// ---------------------------------------------------------------------------
// Project root resolution
// ---------------------------------------------------------------------------
const CONFIG_DIR  = join(homedir(), '.trading_platform')
const CONFIG_FILE = join(CONFIG_DIR, 'electron-project-path')

function saveProjectRoot(root) {
  try { mkdirSync(CONFIG_DIR, { recursive: true }); writeFileSync(CONFIG_FILE, root, 'utf8') } catch (_) {}
}

function findProjectRoot() {
  // Dev mode: src/main/ → ../../.. = project root
  const dev = resolve(__dirname, '../../..')
  if (existsSync(join(dev, '.venv', 'bin', 'python'))) { saveProjectRoot(dev); return dev }
  // Packaged: read saved path
  try {
    const saved = readFileSync(CONFIG_FILE, 'utf8').trim()
    if (saved && existsSync(join(saved, '.venv', 'bin', 'python'))) return saved
  } catch (_) {}
  return null
}

const projectRoot = findProjectRoot()
const venvBin     = projectRoot ? join(projectRoot, '.venv', 'bin') : null
const PORT        = 8765

// ---------------------------------------------------------------------------
// Uvicorn sidecar
// ---------------------------------------------------------------------------
let uvicornProcess = null

async function waitForReady(port, ms = 15000) {
  const deadline = Date.now() + ms
  while (Date.now() < deadline) {
    try { const r = await fetch(`http://127.0.0.1:${port}/health`); if (r.ok) return true } catch (_) {}
    await new Promise(r => setTimeout(r, 400))
  }
  return false
}

async function startSidecar(onReady, onError) {
  if (!projectRoot || !venvBin) return onError('Project root not found.')

  const uvicorn = join(venvBin, 'uvicorn')
  if (!existsSync(uvicorn)) return onError(`uvicorn not found at ${uvicorn}`)

  uvicornProcess = spawn(uvicorn, ['web.api:app', '--host', '127.0.0.1', '--port', String(PORT), '--log-level', 'warning'], {
    cwd: projectRoot,
    env: { ...process.env, PYTHONPATH: projectRoot, PATH: `${venvBin}:${process.env.PATH}` },
  })

  uvicornProcess.stderr.on('data', d => process.stdout.write(`[uvicorn] ${d}`))
  uvicornProcess.on('error', e => onError(e.message))
  uvicornProcess.on('exit', code => { console.log('[uvicorn] exit', code); uvicornProcess = null })

  if (await waitForReady(PORT)) onReady(PORT)
  else onError(`FastAPI server did not start within 15s on port ${PORT}`)
}

function stopSidecar() {
  if (uvicornProcess) { try { uvicornProcess.kill('SIGTERM') } catch (_) {}; uvicornProcess = null }
}

// ---------------------------------------------------------------------------
// Tray
// ---------------------------------------------------------------------------
let tray = null

function createTray() {
  const iconPath = join(__dirname, '../../build/icon.iconset/icon_16x16.png')
  const icon     = nativeImage.createFromPath(iconPath).resize({ width: 16, height: 16 })
  icon.setTemplateImage(true)   // adapts to macOS dark/light menu bar

  tray = new Tray(icon)
  tray.setToolTip('India Trade')
  tray.setTitle('◆')           // replaced with NIFTY level once market opens

  tray.on('click', () => {
    if (!mainWindow) return
    if (mainWindow.isVisible() && mainWindow.isFocused()) {
      mainWindow.hide()
    } else {
      mainWindow.show()
      mainWindow.focus()
    }
  })
}

// ---------------------------------------------------------------------------
// Window
// ---------------------------------------------------------------------------
let mainWindow = null

function createWindow() {
  // Set dock icon explicitly for dev mode (packaged mode uses icon.icns from bundle)
  const appIcon = nativeImage.createFromPath(join(__dirname, '../../build/icon.iconset/icon_512x512.png'))
  if (process.platform === 'darwin' && appIcon && !appIcon.isEmpty()) {
    app.dock.setIcon(appIcon)
  }

  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    icon: appIcon,
    backgroundColor: '#0d0d0d',
    titleBarStyle: 'hiddenInset',
    trafficLightPosition: { x: 16, y: 18 },
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
    show: false,
  })

  if (!app.isPackaged) {
    mainWindow.loadURL('http://localhost:5173')
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
  }

  mainWindow.once('ready-to-show', () => {
    mainWindow.show()
    startSidecar(
      port => { _readyPort = port; mainWindow?.webContents.send('sidecar-ready', { port }) },
      err  => mainWindow?.webContents.send('sidecar-error', { message: err }),
    )
  })

  mainWindow.on('closed', () => { mainWindow = null })
  mainWindow.webContents.setWindowOpenHandler(({ url }) => { shell.openExternal(url); return { action: 'deny' } })
}

// ---------------------------------------------------------------------------
// IPC — renderer can request the current port after HMR / reload
// ---------------------------------------------------------------------------
let _readyPort = null  // set once uvicorn is up

ipcMain.handle('get-port', () => _readyPort)
ipcMain.handle('open-external', (_, url) => shell.openExternal(url))

// Renderer sends live NIFTY/market data to update the tray title
ipcMain.on('update-tray', (_, { label }) => {
  if (tray) tray.setTitle(label ? ` ${label}` : '◆')
})

// ---------------------------------------------------------------------------
// Lifecycle
// ---------------------------------------------------------------------------
app.whenReady().then(() => {
  createTray()
  createWindow()

  // Global shortcut: Cmd+Shift+Space → show/focus the app from anywhere
  globalShortcut.register('CommandOrControl+Shift+Space', () => {
    if (!mainWindow) return
    if (mainWindow.isVisible() && mainWindow.isFocused()) {
      mainWindow.hide()
    } else {
      mainWindow.show()
      mainWindow.focus()
    }
  })
})

app.on('before-quit', () => {
  globalShortcut.unregisterAll()
  stopSidecar()
})
app.on('window-all-closed', () => {
  // On macOS keep the app alive in the tray even when window is closed
  if (process.platform !== 'darwin') { stopSidecar(); app.quit() }
})
