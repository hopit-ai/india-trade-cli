/**
 * useMarketClock
 *
 * Returns live IST market status + NIFTY level, and keeps the tray title updated.
 * Market hours (NSE):
 *   Pre-open : 09:00 – 09:15 IST, Mon–Fri
 *   Open     : 09:15 – 15:30 IST, Mon–Fri
 *   Closed   : everything else
 */
import { useState, useEffect, useRef } from 'react'
import { useChatStore, getBaseUrl } from '../store/chatStore'

const IST_OFFSET_MS = 5.5 * 60 * 60 * 1000   // UTC+5:30

function getISTTime() {
  const now    = new Date()
  const utcMs  = now.getTime() + now.getTimezoneOffset() * 60000
  return new Date(utcMs + IST_OFFSET_MS)
}

function getMarketStatus() {
  const ist      = getISTTime()
  const day      = ist.getDay()           // 0=Sun, 6=Sat
  const hhmm     = ist.getHours() * 100 + ist.getMinutes()

  if (day === 0 || day === 6) return 'closed'
  if (hhmm >= 900  && hhmm < 915)  return 'pre-open'
  if (hhmm >= 915  && hhmm < 1530) return 'open'
  if (hhmm >= 1530 && hhmm < 1600) return 'post-close'
  return 'closed'
}

export function useMarketClock() {
  const port = useChatStore((s) => s.port)
  const [status, setStatus]   = useState(getMarketStatus)
  const [nifty,  setNifty]    = useState(null)   // e.g. "24,512"
  const [banknifty, setBanknifty] = useState(null)
  const pollRef = useRef(null)

  // Update market status every minute
  useEffect(() => {
    const t = setInterval(() => setStatus(getMarketStatus()), 60_000)
    return () => clearInterval(t)
  }, [])

  // Fetch NIFTY quote from sidecar
  async function fetchNifty() {
    if (!port) return
    try {
      const res = await fetch(`${getBaseUrl(port)}/skills/quote`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol: 'NIFTY50', exchange: 'NSE' }),
      })
      if (!res.ok) return
      const data = await res.json()
      const ltp  = data?.data?.ltp ?? data?.ltp
      if (ltp != null) {
        const formatted = Number(ltp).toLocaleString('en-IN', { maximumFractionDigits: 0 })
        setNifty(formatted)
        window.electronAPI?.updateTray({ label: `N ${formatted}` })
      }
    } catch (_) {}
  }

  // Poll NIFTY every 60s when market is open, every 5min otherwise
  useEffect(() => {
    if (!port) return
    if (pollRef.current) clearInterval(pollRef.current)
    fetchNifty()
    const interval = (status === 'open' || status === 'pre-open') ? 60_000 : 300_000
    pollRef.current = setInterval(fetchNifty, interval)
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [port, status])

  // Clear tray when closed
  useEffect(() => {
    if (status === 'closed') {
      window.electronAPI?.updateTray({ label: null })
    }
  }, [status])

  return { status, nifty, banknifty }
}
