import { useState, useEffect, useRef, useCallback } from 'react'

const WS_URL = `ws://${window.location.host}/ws`

export function usePlantData() {
  const [data, setData]         = useState(null)
  const [connected, setConnected] = useState(false)
  const ws = useRef(null)

  useEffect(() => {
    let reconnectTimer = null
    let cancelled = false

    const connect = () => {
      if (cancelled || ws.current?.readyState === WebSocket.OPEN) return

      ws.current = new WebSocket(WS_URL)

      ws.current.onopen = () => setConnected(true)
      ws.current.onclose = () => {
        setConnected(false)
        if (!cancelled) reconnectTimer = setTimeout(connect, 2000)
      }
      ws.current.onerror = () => ws.current?.close()
      ws.current.onmessage = (e) => {
        try {
          setData(JSON.parse(e.data))
        } catch (error) {
          console.error('Failed to parse websocket message', error)
        }
      }
    }

    connect()
    return () => {
      cancelled = true
      if (reconnectTimer) clearTimeout(reconnectTimer)
      ws.current?.close()
    }
  }, [])

  const post = useCallback(async (path, body = {}) => {
    await fetch(path, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(body),
    })
  }, [])

  const postForm = useCallback(async (path, formData) => {
    const response = await fetch(path, {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      const message = await response.text()
      throw new Error(message || 'Request failed')
    }

    return response.json()
  }, [])

  return { data, connected, post, postForm }
}
