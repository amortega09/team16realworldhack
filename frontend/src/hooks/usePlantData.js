import { useState, useEffect, useRef, useCallback } from 'react'

const WS_URL = `ws://${window.location.host}/ws`

export function usePlantData() {
  const [data, setData]         = useState(null)
  const [connected, setConnected] = useState(false)
  const ws = useRef(null)

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return

    ws.current = new WebSocket(WS_URL)

    ws.current.onopen  = () => setConnected(true)
    ws.current.onclose = () => {
      setConnected(false)
      setTimeout(connect, 2000)   // reconnect after 2s
    }
    ws.current.onerror = () => ws.current?.close()
    ws.current.onmessage = (e) => {
      try { setData(JSON.parse(e.data)) } catch {}
    }
  }, [])

  useEffect(() => {
    connect()
    return () => ws.current?.close()
  }, [connect])

  const post = useCallback(async (path, body = {}) => {
    await fetch(path, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(body),
    })
  }, [])

  return { data, connected, post }
}
