/**
 * build-web.js
 * ────────────
 * Copies the built React renderer output to web/static/ and injects
 * the electron-stubs.js script so the app works without Electron IPC.
 *
 * Usage:  node scripts/build-web.js
 * Called by:  npm run build:web
 */

const fs = require('fs')
const path = require('path')

const src = path.join(__dirname, '../out/renderer')
const dest = path.join(__dirname, '../../web/static')

if (!fs.existsSync(src)) {
  console.error('Error: out/renderer not found. Run "electron-vite build" first.')
  process.exit(1)
}

// Create dest dir
fs.mkdirSync(dest, { recursive: true })

// Recursively copy a directory
function copyDir(s, d) {
  fs.mkdirSync(d, { recursive: true })
  for (const entry of fs.readdirSync(s, { withFileTypes: true })) {
    const sp = path.join(s, entry.name)
    const dp = path.join(d, entry.name)
    if (entry.isDirectory()) {
      copyDir(sp, dp)
    } else {
      fs.copyFileSync(sp, dp)
    }
  }
}

// Copy assets directory
const assetsDir = path.join(src, 'assets')
if (fs.existsSync(assetsDir)) {
  copyDir(assetsDir, path.join(dest, 'assets'))
  console.log('  Copied assets/')
}

// Read the original index.html and inject electron stubs
const indexPath = path.join(src, 'index.html')
if (!fs.existsSync(indexPath)) {
  console.error('Error: out/renderer/index.html not found.')
  process.exit(1)
}

let html = fs.readFileSync(indexPath, 'utf8')

// Fix asset paths: ./assets/ → /static/assets/ (absolute, works from any route)
html = html.replace(/\.\/assets\//g, '/static/assets/')

// Inject electron-stubs.js before the first <script> tag (the React bundle)
html = html.replace(
  '<script',
  '<script src="/static/electron-stubs.js"></script>\n    <script'
)

// Write modified index.html
fs.writeFileSync(path.join(dest, 'index.html'), html)

console.log('  Wrote index.html (with electron-stubs.js injected)')
console.log('Web build complete -> web/static/')
