'use strict';

// ---------------------------------------------------------------------------
// xterm.js + node-pty IPC bridge
// nodeIntegration: true lets us require() from node_modules directly
// ---------------------------------------------------------------------------
const { Terminal } = require('@xterm/xterm');
const { FitAddon } = require('@xterm/addon-fit');
const { ipcRenderer } = require('electron');

// ---------------------------------------------------------------------------
// Terminal instance — Claude Code colour palette
// ---------------------------------------------------------------------------
const term = new Terminal({
  fontFamily:
    '"JetBrains Mono", "Fira Code", "Cascadia Code", "SF Mono", Menlo, monospace',
  fontSize: 14,
  lineHeight: 1.45,
  letterSpacing: 0,
  cursorBlink: true,
  cursorStyle: 'bar',
  allowTransparency: false,
  scrollback: 10000,
  theme: {
    background: '#0d0d0d',
    foreground: '#e8e8e8',
    cursor: '#e06c00',       // amber — Claude's accent colour
    cursorAccent: '#0d0d0d',
    selectionBackground: 'rgba(224,108,0,0.25)',

    // Standard ANSI palette (balanced, easy on the eyes on dark bg)
    black:         '#1a1a1a',
    red:           '#e05252',
    green:         '#52e07a',
    yellow:        '#e0b252',
    blue:          '#5294e0',
    magenta:       '#c452e0',
    cyan:          '#52d4e0',
    white:         '#c8c8c8',

    brightBlack:   '#555555',
    brightRed:     '#ff6b6b',
    brightGreen:   '#6bffaa',
    brightYellow:  '#ffd06b',
    brightBlue:    '#6baeff',
    brightMagenta: '#d96bff',
    brightCyan:    '#6bfff0',
    brightWhite:   '#ffffff',
  },
});

const fitAddon = new FitAddon();
term.loadAddon(fitAddon);

// ---------------------------------------------------------------------------
// Mount terminal in the DOM
// ---------------------------------------------------------------------------
const container = document.getElementById('terminal-container');
term.open(container);
fitAddon.fit();

// ---------------------------------------------------------------------------
// Status indicator
// ---------------------------------------------------------------------------
const statusDot  = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');

function setStatus(state) {
  statusDot.className = `status-dot ${state}`;
  statusText.textContent = state === 'connected' ? 'connected' : 'starting…';
}

// ---------------------------------------------------------------------------
// PTY data: main → renderer
// ---------------------------------------------------------------------------
ipcRenderer.on('pty-data', (_, data) => {
  term.write(data);

  // Mark connected on first real output
  if (statusText.textContent !== 'connected') {
    setStatus('connected');
  }
});

// ---------------------------------------------------------------------------
// Keyboard input: renderer → main (PTY)
// ---------------------------------------------------------------------------
term.onData((data) => {
  ipcRenderer.send('pty-input', data);
});

// ---------------------------------------------------------------------------
// Resize: keep PTY cols/rows in sync with window size
// ---------------------------------------------------------------------------
function fitAndResize() {
  fitAddon.fit();
  ipcRenderer.send('pty-resize', { cols: term.cols, rows: term.rows });
}

window.addEventListener('resize', fitAndResize);
ipcRenderer.on('window-resized', fitAndResize);

// ---------------------------------------------------------------------------
// Bootstrap: tell main process our initial size so it spawns the PTY
// correctly, then do an initial fit after a tick (fonts need to load first).
// ---------------------------------------------------------------------------
setTimeout(() => {
  fitAddon.fit();
  ipcRenderer.send('pty-ready', { cols: term.cols, rows: term.rows });
}, 50);
