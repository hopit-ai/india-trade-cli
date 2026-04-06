'use strict';

const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const fs = require('fs');

let mainWindow = null;
let ptyProcess = null;

// ---------------------------------------------------------------------------
// Resolve the project root (one level up from macos-app/) so we can inject
// the virtualenv's bin directory into PATH even when launched as a .app.
// ---------------------------------------------------------------------------
const projectRoot = path.resolve(__dirname, '..');
const venvBin = path.join(projectRoot, '.venv', 'bin');

function buildEnv() {
  const env = { ...process.env };
  env.TERM = 'xterm-256color';
  env.COLORTERM = 'truecolor';
  env.LANG = env.LANG || 'en_US.UTF-8';

  // Inject .venv/bin so `trade` is found even when launched from Finder
  if (fs.existsSync(venvBin)) {
    env.PATH = `${venvBin}:${env.PATH || '/usr/local/bin:/usr/bin:/bin'}`;
  }

  // Ensure Python can find the `app` package regardless of which Python
  // environment the shell activates (conda base, system, etc.)
  env.PYTHONPATH = projectRoot;

  return env;
}

// ---------------------------------------------------------------------------
// PTY — spawn the user's login shell, then auto-launch `trade`
// ---------------------------------------------------------------------------
function spawnPty(cols, rows) {
  let pty;
  try {
    pty = require('node-pty');
  } catch (e) {
    console.error('[main] node-pty failed to load:', e.message);
    return;
  }

  // Spawn the venv Python directly — no shell prompt, no session restore,
  // goes straight to the trade banner.
  const python = path.join(venvBin, 'python');
  const entry   = path.join(projectRoot, 'app', 'main.py');

  ptyProcess = pty.spawn(python, [entry], {
    name: 'xterm-256color',
    cols: cols || 120,
    rows: rows || 35,
    cwd: projectRoot,
    env: buildEnv(),
  });

  ptyProcess.onData((data) => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('pty-data', data);
    }
  });

  ptyProcess.onExit(() => {
    ptyProcess = null;
    if (mainWindow && !mainWindow.isDestroyed()) {
      // Give the user a moment to see any final output, then quit
      setTimeout(() => app.quit(), 500);
    }
  });
}

function killPty() {
  if (ptyProcess) {
    try { ptyProcess.kill(); } catch (_) {}
    ptyProcess = null;
  }
}

// ---------------------------------------------------------------------------
// Window
// ---------------------------------------------------------------------------
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1100,
    height: 750,
    minWidth: 800,
    minHeight: 500,
    backgroundColor: '#0d0d0d',

    // macOS: hide the default title bar but keep traffic-light buttons
    titleBarStyle: 'hiddenInset',
    trafficLightPosition: { x: 16, y: 18 },

    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
      sandbox: false,
    },

    // Don't flash white before the dark background loads
    show: false,
  });

  mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'));

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  mainWindow.on('resize', () => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('window-resized');
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
    killPty();
  });
}

// ---------------------------------------------------------------------------
// IPC handlers (renderer → main)
// ---------------------------------------------------------------------------
ipcMain.on('pty-input', (_, data) => {
  if (ptyProcess) ptyProcess.write(data);
});

ipcMain.on('pty-resize', (_, { cols, rows }) => {
  if (ptyProcess) ptyProcess.resize(cols, rows);
});

// Renderer tells us its initial size so we can spawn PTY with right dimensions
ipcMain.once('pty-ready', (_, { cols, rows }) => {
  spawnPty(cols, rows);
});

// ---------------------------------------------------------------------------
// App lifecycle
// ---------------------------------------------------------------------------
app.whenReady().then(createWindow);

app.on('before-quit', killPty);

app.on('window-all-closed', () => {
  killPty();
  app.quit();
});
