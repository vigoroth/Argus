import { useEffect, useState } from 'react'
import type { SecretStatus } from '../api'
import { getSecrets, setSecret } from '../api'

const PROVIDERS: { id: string; label: string }[] = [
  { id: 'openai', label: 'OpenAI' },
  { id: 'anthropic', label: 'Anthropic' },
  { id: 'google', label: 'Google Gemini' },
]

function KeyRow({ id, label, isSet, onSaved }: {
  id: string; label: string; isSet: boolean; onSaved: () => void
}) {
  const [val, setVal] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  const save = async () => {
    if (!val.trim()) return
    setBusy(true); setErr('')
    try {
      await setSecret(id, val.trim())
      setVal('')
      onSaved()
    } catch (e) { setErr(String(e)) } finally { setBusy(false) }
  }

  return (
    <div style={{ background: 'var(--rail)', border: '1px solid var(--hair-1)',
                  borderRadius: 12, padding: '14px 16px', marginBottom: 12 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
        <span style={{ fontSize: 15, fontWeight: 620 }}>{label}</span>
        <span style={{ fontSize: 11, letterSpacing: .5, padding: '2px 8px', borderRadius: 999,
                       color: isSet ? 'var(--green)' : 'var(--faint)',
                       border: '1px solid ' + (isSet ? 'var(--green)' : 'var(--hair-2)') }}>
          {isSet ? 'set' : 'not set'}
        </span>
      </div>
      <div style={{ display: 'flex', gap: 8 }}>
        <input type="password" value={val} onChange={e => setVal(e.target.value)}
               placeholder={isSet ? 'enter a new key to replace' : 'paste API key'}
               onKeyDown={e => { if (e.key === 'Enter') save() }}
               style={{ flex: 1, padding: '8px 11px', background: 'var(--hover)',
                        border: '1px solid var(--hair-2)', borderRadius: 8, color: 'var(--text)',
                        fontSize: 13, outline: 'none' }}/>
        <button onClick={save} disabled={busy || !val.trim()}
                style={{ padding: '8px 16px', borderRadius: 8, border: '1px solid var(--pill-br)',
                         background: 'var(--pill-on)', color: 'var(--text)', fontSize: 13,
                         cursor: busy || !val.trim() ? 'default' : 'pointer',
                         opacity: busy || !val.trim() ? .5 : 1 }}>
          {busy ? 'Saving…' : 'Save'}
        </button>
      </div>
      {err && <div style={{ color: 'var(--grad-a)', fontSize: 12, marginTop: 6 }}>{err}</div>}
    </div>
  )
}

export default function KeysView() {
  const [status, setStatus] = useState<SecretStatus>({})
  const refresh = () => getSecrets().then(setStatus).catch(console.error)
  useEffect(() => { refresh() }, [])

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: '28px 36px' }}>
      <div style={{ maxWidth: 620, margin: '0 auto' }}>
        <h2 style={{ fontSize: 20, fontWeight: 680, marginBottom: 6 }}>API Keys</h2>
        <p style={{ color: 'var(--muted)', fontSize: 13, lineHeight: 1.6, marginBottom: 20 }}>
          Keys are encrypted at rest and applied immediately — no restart. For security
          they are write-only: existing values are never shown, only whether a key is set.
        </p>
        {PROVIDERS.map(p => (
          <KeyRow key={p.id} id={p.id} label={p.label} isSet={!!status[p.id]} onSaved={refresh}/>
        ))}
      </div>
    </div>
  )
}
