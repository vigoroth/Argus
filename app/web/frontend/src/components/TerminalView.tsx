import { useEffect, useRef } from 'react'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import '@xterm/xterm/css/xterm.css'

export default function TerminalView() {
  const mountRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!mountRef.current) return
    const term = new Terminal({
      fontFamily: "'JetBrains Mono', ui-monospace, monospace",
      fontSize: 13.5,
      cursorBlink: true,
      theme: {
        background: '#0b0d10',
        foreground: '#d6dae0',
        cursor: '#9b8cff',
        selectionBackground: '#221f4c',
        black: '#0b0d10', brightBlack: '#4d535b',
        blue: '#5fb4e6', brightBlue: '#7cc4ee',
        magenta: '#9b8cff', brightMagenta: '#b3a6ff',
        green: '#5fb84f', brightGreen: '#7ccb6e',
        red: '#e34948', brightRed: '#e66767',
        yellow: '#f4bf4f', brightYellow: '#f7d27e',
        cyan: '#5fb4e6', brightCyan: '#8ed0f0',
        white: '#c8ccd2', brightWhite: '#ffffff',
      },
    })
    const fit = new FitAddon()
    term.loadAddon(fit)
    term.open(mountRef.current)
    fit.fit()

    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${proto}://${window.location.host}/term`)
    ws.binaryType = 'arraybuffer'

    ws.onopen = () => {
      ws.send(JSON.stringify({ resize: [term.cols, term.rows] }))
      term.focus()
    }
    ws.onmessage = e => term.write(typeof e.data === 'string' ? e.data : new Uint8Array(e.data))
    ws.onclose = () => term.write('\r\n\x1b[38;5;103m[session closed]\x1b[0m\r\n')
    ws.onerror = () => term.write('\r\n\x1b[31m[connection error]\x1b[0m\r\n')

    const dataSub = term.onData(d => { if (ws.readyState === WebSocket.OPEN) ws.send(d) })
    const resize = () => {
      fit.fit()
      if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ resize: [term.cols, term.rows] }))
    }
    window.addEventListener('resize', resize)

    return () => {
      window.removeEventListener('resize', resize)
      dataSub.dispose()
      ws.close()
      term.dispose()
    }
  }, [])

  return (
    <div style={{ flex: 1, minHeight: 0, padding: '10px 14px 14px', background: '#0b0d10' }}>
      <div ref={mountRef} style={{ width: '100%', height: '100%' }}/>
    </div>
  )
}
