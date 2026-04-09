/**
 * pythonBootstrap.js
 * ──────────────────
 * Detects Python 3.11+, creates a venv at ~/.trading_platform/venv/,
 * and installs the india-trade-cli wheel into it.
 *
 * First launch: detect → create venv → pip install wheel → ~2 min
 * Subsequent:   detect → venv exists + version matches → ~1 sec
 */

import { existsSync, readFileSync, writeFileSync, mkdirSync } from 'fs'
import { join } from 'path'
import { homedir } from 'os'
import { spawn, execFileSync } from 'child_process'
import { app } from 'electron'

// ── Paths ────────────────────────────────────────────────────────

const PLATFORM_DIR = join(homedir(), '.trading_platform')
const VENV_PATH    = join(PLATFORM_DIR, 'venv')
const VENV_BIN     = join(VENV_PATH, 'bin')
const VENV_PYTHON  = join(VENV_BIN, 'python')
const VENV_PIP     = join(VENV_BIN, 'pip')
const VENV_UVICORN = join(VENV_BIN, 'uvicorn')
const VERSION_STAMP = join(VENV_PATH, '.app-version')

// Minimum Python version required
const MIN_PYTHON_MAJOR = 3
const MIN_PYTHON_MINOR = 11

// ── Python Detection ─────────────────────────────────────────────

const PYTHON_CANDIDATES = [
  'python3',
  '/opt/homebrew/bin/python3',
  '/usr/local/bin/python3',
  '/usr/bin/python3',
  '/opt/homebrew/bin/python3.12',
  '/opt/homebrew/bin/python3.13',
  '/usr/local/bin/python3.12',
  '/usr/local/bin/python3.13',
]

function parsePythonVersion(versionString) {
  const match = versionString.match(/Python (\d+)\.(\d+)\.(\d+)/)
  if (!match) return null
  return { major: parseInt(match[1]), minor: parseInt(match[2]), patch: parseInt(match[3]) }
}

function tryPythonCandidate(candidate) {
  try {
    const output = execFileSync(candidate, ['--version'], {
      encoding: 'utf8',
      timeout: 5000,
      env: { ...process.env, PATH: `/opt/homebrew/bin:/usr/local/bin:/usr/bin:${process.env.PATH}` },
    }).trim()
    const version = parsePythonVersion(output)
    if (!version) return null
    if (version.major < MIN_PYTHON_MAJOR) return null
    if (version.major === MIN_PYTHON_MAJOR && version.minor < MIN_PYTHON_MINOR) return null
    return { path: candidate, version }
  } catch {
    return null
  }
}

export function detectPython() {
  for (const candidate of PYTHON_CANDIDATES) {
    const result = tryPythonCandidate(candidate)
    if (result) return result
  }
  return null
}

// ── Venv Management ──────────────────────────────────────────────

export function checkVenv() {
  if (!existsSync(VENV_PYTHON)) return false
  // Verify the Python binary actually works (symlinks might be broken)
  try {
    execFileSync(VENV_PYTHON, ['--version'], { encoding: 'utf8', timeout: 5000 })
    return true
  } catch {
    return false
  }
}

export function checkDepsVersion() {
  if (!existsSync(VERSION_STAMP)) return false
  try {
    const stamped = readFileSync(VERSION_STAMP, 'utf8').trim()
    const current = app.getVersion()
    return stamped === current
  } catch {
    return false
  }
}

function writeVersionStamp() {
  writeFileSync(VERSION_STAMP, app.getVersion(), 'utf8')
}

// ── Subprocess helpers ───────────────────────────────────────────

function runProcess(cmd, args, opts = {}) {
  return new Promise((resolve, reject) => {
    const proc = spawn(cmd, args, {
      env: { ...process.env, PATH: `/opt/homebrew/bin:/usr/local/bin:/usr/bin:${process.env.PATH}` },
      ...opts,
    })
    let stdout = ''
    let stderr = ''

    proc.stdout?.on('data', (d) => {
      stdout += d.toString()
      opts.onStdout?.(d.toString())
    })
    proc.stderr?.on('data', (d) => {
      stderr += d.toString()
      opts.onStderr?.(d.toString())
    })
    proc.on('error', (err) => reject(new Error(`Failed to start ${cmd}: ${err.message}`)))
    proc.on('exit', (code) => {
      if (code === 0) resolve({ stdout, stderr })
      else reject(Object.assign(new Error(`${cmd} exited with code ${code}`), { stderr: stderr.slice(-2000) }))
    })

    // Timeout
    const timeout = opts.timeout ?? 300000 // 5 min default
    const timer = setTimeout(() => {
      proc.kill('SIGTERM')
      reject(new Error(`${cmd} timed out after ${timeout / 1000}s`))
    }, timeout)
    proc.on('exit', () => clearTimeout(timer))
  })
}

// ── Core Bootstrap ───────────────────────────────────────────────

async function createVenv(pythonPath, onProgress) {
  onProgress?.({ stage: 'creating_venv', message: 'Creating Python environment...' })
  mkdirSync(PLATFORM_DIR, { recursive: true })
  await runProcess(pythonPath, ['-m', 'venv', VENV_PATH], { timeout: 60000 })
}

function findWheelPath() {
  const { readdirSync } = require('fs')

  // Packaged mode: extraResources/python-pkg/
  if (app.isPackaged) {
    const resourceDir = join(process.resourcesPath, 'python-pkg')
    if (existsSync(resourceDir)) {
      const wheels = readdirSync(resourceDir).filter(f => f.endsWith('.whl'))
      if (wheels.length > 0) return join(resourceDir, wheels[0])
    }
  }

  // Dev mode: macos-app/dist/
  const devDir = join(__dirname, '../../dist')
  if (existsSync(devDir)) {
    const wheels = readdirSync(devDir).filter(f => f.endsWith('.whl'))
    if (wheels.length > 0) return join(devDir, wheels[0])
  }

  return null
}

async function installDeps(onProgress) {
  onProgress?.({ stage: 'installing_deps', message: 'Installing dependencies (first time only)...', percent: 0 })

  const wheelPath = findWheelPath()

  // Upgrade pip first
  await runProcess(VENV_PIP, ['install', '--upgrade', 'pip'], { timeout: 60000 })

  if (wheelPath) {
    // Install from bundled wheel
    let lineCount = 0
    await runProcess(VENV_PIP, ['install', wheelPath, '--no-input'], {
      timeout: 600000, // 10 min for scipy etc.
      onStdout: (line) => {
        lineCount++
        // Rough progress: ~50 packages, each emits 1-3 lines
        const percent = Math.min(95, Math.round(lineCount / 150 * 100))
        onProgress?.({ stage: 'installing_deps', message: `Installing packages...`, percent })
      },
    })
  } else {
    // Fallback: install from project root (dev mode without wheel)
    const projectRoot = join(__dirname, '../../..')
    if (existsSync(join(projectRoot, 'pyproject.toml'))) {
      let lineCount = 0
      await runProcess(VENV_PIP, ['install', '-e', projectRoot, '--no-input'], {
        timeout: 600000,
        onStdout: (line) => {
          lineCount++
          const percent = Math.min(95, Math.round(lineCount / 150 * 100))
          onProgress?.({ stage: 'installing_deps', message: `Installing packages...`, percent })
        },
      })
    } else {
      throw new Error('No wheel or pyproject.toml found. Cannot install dependencies.')
    }
  }

  writeVersionStamp()
  onProgress?.({ stage: 'installing_deps', message: 'Dependencies installed.', percent: 100 })
}

function findSourceRoot() {
  // After pip install, the source is in site-packages or editable install
  try {
    const output = execFileSync(VENV_PYTHON, ['-c', 'import web.api; import os; print(os.path.dirname(os.path.dirname(web.api.__file__)))'], {
      encoding: 'utf8',
      timeout: 10000,
    }).trim()
    if (output && existsSync(output)) return output
  } catch { /* fallback below */ }

  // Fallback for editable installs: project root
  const projectRoot = join(__dirname, '../../..')
  if (existsSync(join(projectRoot, 'web', 'api.py'))) return projectRoot

  throw new Error('Could not find Python source root after installation.')
}

// ── Main Entry Point ─────────────────────────────────────────────

export async function ensurePythonEnv(onProgress) {
  // Dev mode shortcut: use repo .venv if it exists
  if (!app.isPackaged) {
    const devRoot = join(__dirname, '../../..')
    const devVenvPython = join(devRoot, '.venv', 'bin', 'python')
    if (existsSync(devVenvPython)) {
      onProgress?.({ stage: 'starting', message: 'Using development environment...' })
      return {
        venvBin: join(devRoot, '.venv', 'bin'),
        sourceRoot: devRoot,
      }
    }
  }

  // Step 1: Detect Python
  onProgress?.({ stage: 'detecting', message: 'Checking for Python...' })
  const python = detectPython()
  if (!python) {
    const err = new Error('Python 3.11 or later is required but was not found on this system.')
    err.isPythonMissing = true
    throw err
  }
  onProgress?.({ stage: 'detecting', message: `Found Python ${python.version.major}.${python.version.minor}.${python.version.patch}` })

  // Step 2: Check venv
  const venvExists = checkVenv()
  const versionMatch = venvExists && checkDepsVersion()

  if (venvExists && versionMatch) {
    // Fast path: venv ready, skip setup
    onProgress?.({ stage: 'starting', message: 'Environment ready.' })
    return { venvBin: VENV_BIN, sourceRoot: findSourceRoot() }
  }

  // Step 3: Create venv if needed
  if (!venvExists) {
    await createVenv(python.path, onProgress)
  }

  // Step 4: Install / update dependencies
  await installDeps(onProgress)

  return { venvBin: VENV_BIN, sourceRoot: findSourceRoot() }
}

export { VENV_PATH, VENV_BIN }
