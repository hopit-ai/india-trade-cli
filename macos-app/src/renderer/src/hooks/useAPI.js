import { useChatStore } from '../store/chatStore'

export function useAPI() {
  const port = useChatStore((s) => s.port)
  const base = port ? `http://127.0.0.1:${port}` : null

  const call = async (endpoint, body = {}) => {
    if (!base) throw new Error('API not ready — sidecar is still starting')
    const res = await fetch(`${base}${endpoint}`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(body),
    })
    if (!res.ok) {
      const err = await res.text()
      throw new Error(`API ${res.status}: ${err}`)
    }
    return res.json()
  }

  const get = async (endpoint) => {
    if (!base) throw new Error('API not ready')
    const res = await fetch(`${base}${endpoint}`)
    if (!res.ok) throw new Error(`API ${res.status}`)
    return res.json()
  }

  return { call, get, ready: !!base, base }
}
