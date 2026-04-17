# Spec: Automated DMG Build + GitHub Releases (#140)

## Problem
The macOS Electron app DMG is built manually with `npm run build`. No automated
process to build, version, and publish releases.

## Solution: GitHub Actions workflow

### .github/workflows/build-mac.yml
- **Trigger**: tag push (`v0.2.0`) or manual dispatch
- **Runner**: `macos-latest` (for Electron + DMG packaging)
- **Steps**:
  1. Checkout
  2. Python 3.12 + Node 20
  3. `pip install -e .` (Python dependencies)
  4. `npm ci` + `npm run build:web` (React web app)
  5. `npm run build` (Electron DMG with `electron-builder`)
  6. Upload DMG as GitHub Actions artifact (30-day retention)
  7. Create GitHub Release with DMG attached (on tag push)

### Code signing
- `CSC_IDENTITY_AUTO_DISCOVERY: false` — skips signing in CI (no Apple cert)
- Users can bypass Gatekeeper via right-click → Open on first launch
- Signing/notarization documented as future work

### Versioning
- Tag `v0.2.0` → version `0.2.0`
- Manual dispatch → uses input version or "dev"

## Files
- `.github/workflows/build-mac.yml` — CI workflow

## Acceptance Criteria
- Workflow YAML is valid and parseable
- Triggers on `v*` tags and manual dispatch
- Uploads DMG as artifact
- Creates GitHub Release on tag push
- CSC_IDENTITY_AUTO_DISCOVERY=false to avoid signing errors in CI
