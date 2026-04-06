'use strict'

const { spawn } = require('child_process')
const path = require('path')
const fs = require('fs')
const os = require('os')

const CONFIG_DIR  = path.join(os.homedir(), '.trading_platform')
const CONFIG_FILE = path.join(CONFIG_DIR, 'electron-project-path')
const PORT = 8765

let uvicornProcess = null
let _projectRoot   = null

// ---------------------------------------------------------------------------
// Project root resolution (same logic as Level 2 main.js)
// ---------------------------------------------------------------------------
function saveProjectRoot(root) {
  try {
    fs.mkdirSync(CONFIG_DIR, { recursive: true })
    fs.writeFileSync(CONFIG_FILE, root, 'utf8')
  } catch (_) {}
}

function findProjectRoot() {
  const devCandidate = path.resolve(__dirname, '../../..')
  if (fs.existsSync(path.join(devCandidate, '.venv', 'bin', 'python'))) {
    saveProjectRoot(devCandidate)
    return devCandidate
  }
  try {
    const saved = fs.readFileSync(CONFIG_FILE, 'utf8').trim()
    if (saved && fs.existsSync(path.join(saved, '.venv', 'bin', 'python'))) {
      return saved
    }
  } catch (_) {}
  return null
}

function getProjectRoot() {
  if (!_projectRoot) _projectRoot = findProjectRoot()
  return _projectRoot
}

// ---------------------------------------------------------------------------
// Health check — poll until the FastAPI server responds
// ---------------------------------------------------------------------------
async function waitForReady(port, timeoutMs = 15000) {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    try {
      // Node 18+ has global fetch
      const res = await fetch(`http://127.0.0.1:${port}/health`)
      if (res.ok) return true
    } catch (_) {}
    await new Promise(r => setTimeout(r, 300))
  }
  return false
}

// ---------------------------------------------------------------------------
// Start uvicorn
// ---------------------------------------------------------------------------
async function startSidecar(onReady, onError) {
  const projectRoot = getProjectRoot()
  if (!projectRoot) {
    onError('Project root not found. Run npm run dev once from the project directory first.')
    return
  }

  const uvicorn = path.join(projectRoot, '.venv', 'bin', 'uvicorn')
  if (!fs.existsSync(uvicorn)) {
    onError(`uvicorn not found at ${uvicorn}`)
    return
  }

  uvicornProcess = spawn(uvicorn, [
    'web.api:app',
    '--host', '127.0.0.1',
    '--port', String(PORT),
    '--log-level', 'warning',
  ], {
    cwd: projectRoot,
    env: {
      ...process.env,
      PYTHONPATH: projectRoot,
      PATH: `${path.join(projectRoot, '.venv', 'bin')}:${process.env.PATH}`,
    },
  })

  uvicornProcess.stderr.on('data', (d) => console.log('[uvicorn]', d.toString().trim()))
  uvicornProcess.stdout.on('data', (d) => console.log('[uvicorn]', d.toString().trim()))

  uvicornProcess.on('error', (err) => {
    console.error('[uvicorn] spawn error:', err.message)
    onError(err.message)
  })

  uvicornProcess.on('exit', (code) => {
    console.log('[uvicorn] exited with code', code)
    uvicornProcess = null
  })

  // Poll until ready
  const ready = await waitForReady(PORT)
  if (ready) {
    console.log(`[uvicorn] ready on port ${PORT}`)
    onReady(PORT)
  } else {
    onError(`FastAPI server did not start within 15s on port ${PORT}`)
  }
}

function stopSidecar() {
  if (uvicornProcess) {
    uvicornProcess.kill('SIGTERM')
    uvicornProcess = null
  }
}

module.exports = { startSidecar, stopSidecar, getProjectRoot, PORT }
