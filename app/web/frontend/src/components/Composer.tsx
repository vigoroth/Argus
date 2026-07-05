import { useRef, useState } from 'react'
import type { ModelsByProvider } from '../api'
import { Bars, Term, ArrowUp, ChevronDown } from './Icons'

export default function Composer({ models, disabled, onSend, onTerminal, termEnabled }: {
  models: ModelsByProvider; disabled: boolean
  onSend: (msg: string, provider: string | null, model: string | null, mode: string) => void
  onTerminal: () => void
  termEnabled: boolean
}) {
  const [msg, setMsg] = useState('')
  const [mode, setMode] = useState<'agent' | 'chat'>('agent')
  const [provider, setProvider] = useState('')
  const [model, setModel] = useState('')
  const [pickerOpen, setPickerOpen] = useState(false)
  const taRef = useRef<HTMLTextAreaElement>(null)

  const send = () => {
    const m = msg.trim()
    if (!m || disabled) return
    setMsg('')
    if (taRef.current) taRef.current.style.height = 'auto'
    onSend(m, provider || null, model || null, mode)
  }

  const pillBtn = (m: 'agent' | 'chat', label: string) => (
    <button onClick={() => setMode(m)}
      style={{ padding: '6px 16px', border: 'none', borderRadius: 7, fontSize: 13.5,
               cursor: 'pointer', background: mode === m ? 'var(--pill-on)' : 'transparent',
               color: mode === m ? 'var(--pill-fg)' : 'var(--muted)' }}>{label}</button>
  )

  return (
    <div style={{ padding: '0 36px 40px', display: 'flex', justifyContent: 'center' }}>
      <div style={{ width: '100%', maxWidth: 1030, background: 'var(--composer)',
                    border: '1px solid var(--hair-2)', borderRadius: 16,
                    padding: '18px 20px 14px', boxShadow: '0 8px 30px rgba(0,0,0,.35)' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 16 }}>
          <textarea ref={taRef} rows={1} placeholder="Message Argus ..." value={msg}
            onChange={e => {
              setMsg(e.target.value)
              const t = e.target; t.style.height = 'auto'
              t.style.height = Math.min(t.scrollHeight, 160) + 'px'
            }}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
            style={{ flex: 1, background: 'transparent', border: 'none', outline: 'none',
                     resize: 'none', color: 'var(--text)', fontSize: 15, lineHeight: 1.5,
                     maxHeight: 160, overflowY: 'auto' }}/>
          <div style={{ position: 'relative' }}>
            <div onClick={() => setPickerOpen(o => !o)}
                 style={{ display: 'flex', alignItems: 'center', gap: 7, color: 'var(--muted)',
                          fontSize: 13, whiteSpace: 'nowrap', cursor: 'pointer', paddingTop: 2 }}>
              <Bars size={15}/><span>{model || 'default'}</span><ChevronDown size={13}/>
            </div>
            {pickerOpen && (
              <div style={{ position: 'absolute', right: 0, bottom: '130%', background: 'var(--rail)',
                            border: '1px solid var(--hair-2)', borderRadius: 10, padding: 8,
                            zIndex: 20, minWidth: 220, maxHeight: 300, overflowY: 'auto' }}>
                {Object.entries(models).map(([prov, list]) => (
                  <div key={prov}>
                    <div style={{ color: 'var(--faint)', fontSize: 11, padding: '6px 8px 2px',
                                  textTransform: 'uppercase', letterSpacing: 1 }}>{prov}</div>
                    {list.map(m => (
                      <div key={m}
                           onClick={() => { setProvider(prov); setModel(m); setPickerOpen(false) }}
                           style={{ padding: '6px 8px', borderRadius: 6, cursor: 'pointer', fontSize: 12.5,
                                    color: m === model ? 'var(--pill-fg)' : 'var(--text-2)',
                                    background: m === model ? 'var(--pill-on)' : 'transparent' }}>
                        {m}
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {termEnabled && (
              <button onClick={onTerminal} title="Terminal"
                style={{ width: 36, height: 34, display: 'flex', alignItems: 'center',
                         justifyContent: 'center', background: 'var(--btn-bg)',
                         border: '1px solid var(--hair-2)', borderRadius: 8,
                         color: 'var(--muted)', cursor: 'pointer' }}>
                <Term size={16}/>
              </button>
            )}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ display: 'flex', background: 'var(--pill-bg)',
                          border: '1px solid var(--pill-br)', borderRadius: 9, padding: 3, gap: 2 }}>
              {pillBtn('agent', 'Agent')}
              {pillBtn('chat', 'Chat')}
            </div>
            <button onClick={send} disabled={disabled}
              style={{ width: 40, height: 38, display: 'flex', alignItems: 'center',
                       justifyContent: 'center', border: 'none', borderRadius: 9,
                       cursor: disabled ? 'default' : 'pointer', opacity: disabled ? .5 : 1,
                       background: 'linear-gradient(180deg,var(--send-a),var(--send-b))',
                       boxShadow: '0 2px 12px rgba(96,80,230,.45)' }}>
              <ArrowUp size={18} color="#f1eeff"/>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
