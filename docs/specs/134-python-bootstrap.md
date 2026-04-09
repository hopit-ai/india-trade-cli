# Spec: macOS App Python Bootstrap (#134)

## Problem
The macOS Electron app requires a pre-existing `.venv` at the repo root. Packaged DMG has no Python — app fails on first launch for anyone without the repo cloned.

## Solution
Auto-detect Python 3.11+ on the system, create a venv at `~/.trading_platform/venv/`, install dependencies from a bundled wheel, and start the sidecar.

## Requirements

### Python Detection
- Check candidates in order: `python3` on PATH, `/opt/homebrew/bin/python3`, `/usr/local/bin/python3`, `/usr/bin/python3`, versioned variants (3.12, 3.13)
- Parse version string from `python3 --version`
- Accept >= 3.11 only
- Return first valid candidate

### Venv Management
- Venv path: `~/.trading_platform/venv/`
- Check: `venv/bin/python` exists AND executes successfully
- Version stamp: `venv/.app-version` contains app version from package.json
- If stamp mismatches: reinstall deps (app updated)

### Dependency Installation
- Packaged mode: `pip install` bundled `.whl` from `extraResources/python-pkg/`
- Dev mode fallback: `pip install -e .` from project root
- Timeout: 10 min (scipy is large)
- Progress: parse pip stdout lines for rough percentage

### Dev Mode Shortcut
- If `!app.isPackaged` and `.venv/bin/python` exists at repo root (3 dirs up): use it directly
- Skip all bootstrap steps
- Preserves existing developer workflow

### Setup Screen UI
- Progress state: message + progress bar (indeterminate for detect/venv, determinate for pip install)
- Python missing state: install instructions (python.org link + brew command) + Retry button
- Error state: error message + expandable details + Retry + Reset Environment button

### IPC Channels
- `setup-progress`: `{ stage, message, percent? }`
- `setup-python-missing`: `{ message, installUrl, brewCommand }`
- `sidecar-ready`: `{ port }`
- `sidecar-error`: `{ message, details? }`
- `retry-setup`: trigger re-bootstrap
- `reset-venv`: delete venv + re-bootstrap

### Startup Flow
| Scenario | Steps | Time |
|----------|-------|------|
| First launch | detect → create venv → pip install → start sidecar | ~2 min |
| Subsequent | detect → venv exists + version match → start sidecar | ~2 sec |
| App update | detect → venv exists + version mismatch → pip install → start sidecar | ~1 min |
| No Python | detect fails → show install instructions | instant |

## Acceptance Criteria
1. Dev mode (`npm run dev`) works unchanged when `.venv` exists at repo root
2. With `.venv` removed + `~/.trading_platform/venv/` removed, app shows SetupScreen and bootstraps
3. After bootstrap, app loads normally with sidecar on port 8765
4. Subsequent launch skips setup (< 3 sec to sidecar-ready)
5. Changing version in package.json triggers reinstall on next launch
6. Reset Environment button deletes venv and re-bootstraps
7. If Python not found, shows clear install instructions with Retry
