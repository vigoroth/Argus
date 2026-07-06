import { useEffect, useState } from 'react'
import type { PullProgress, SecretStatus } from '../api'
import { deleteModel, getModels, getSecrets, pullModel, setSecret } from '../api'

const PRESETS = ['llama3.2:3b', 'qwen3:8b', 'mistral:7b', 'hf.co/bartowski/Llama-3.2-3B-Instruct-GGUF:Q4_K_M']

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

function ModelsSection() {
  const [local, setLocal] = useState<string[]>([])
  const [name, setName] = useState('')
  const [pulling, setPulling] = useState<string | null>(null)
  const [prog, setProg] = useState<PullProgress | null>(null)
  const [err, setErr] = useState('')

  const refresh = () => getModels().then(m => setLocal(m.ollama ?? [])).catch(console.error)
  useEffect(() => { refresh() }, [])

  const pull = async (n: string) => {
    const model = n.trim()
    if (!model || pulling) return
    setPulling(model); setProg(null); setErr('')
    try {
      await pullModel(model,
        p => setProg(p),
        () => { setPulling(null); setProg(null); setName(''); refresh() },
        e => { setErr(e); setPulling(null); setProg(null) })
    } catch { /* onError surfaced it */ setPulling(null) }
  }

  const remove = async (n: string) => {
    if (!window.confirm(`Delete local model "${n}"?`)) return
    await deleteModel(n)
    refresh()
  }

  const pct = prog?.total ? Math.round(100 * (prog.completed ?? 0) / prog.total) : null
  const input: React.CSSProperties = { flex: 1, padding: '8px 11px', background: 'var(--hover)',
    border: '1px solid var(--hair-2)', borderRadius: 8, color: 'var(--text)', fontSize: 13, outline: 'none' }

  return (
    <>
      <h2 style={{ fontSize: 20, fontWeight: 680, margin: '30px 0 6px' }}>Local models</h2>
      <p style={{ color: 'var(--muted)', fontSize: 13, lineHeight: 1.6, marginBottom: 14 }}>
        Pull models through Ollama — registry names (<code>llama3.2:3b</code>) or Hugging Face
        GGUFs (<code>hf.co/org/repo:quant</code>). Downloads are multi-GB; progress shows below.
      </p>

      <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
        <input value={name} onChange={e => setName(e.target.value)}
               placeholder="model name, e.g. llama3.2:3b or hf.co/org/repo:Q4_K_M"
               onKeyDown={e => { if (e.key === 'Enter') pull(name) }}
               disabled={!!pulling} style={input}/>
        <button onClick={() => pull(name)} disabled={!!pulling || !name.trim()}
                style={{ padding: '8px 16px', borderRadius: 8, border: '1px solid var(--pill-br)',
                         background: 'var(--pill-on)', color: 'var(--text)', fontSize: 13,
                         cursor: pulling || !name.trim() ? 'default' : 'pointer',
                         opacity: pulling || !name.trim() ? .5 : 1 }}>
          {pulling ? 'Pulling…' : 'Pull'}
        </button>
      </div>

      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 14 }}>
        {PRESETS.map(p => (
          <button key={p} onClick={() => setName(p)} disabled={!!pulling}
                  style={{ padding: '3px 10px', borderRadius: 999, fontSize: 11.5,
                           background: 'var(--hover)', border: '1px solid var(--hair-2)',
                           color: 'var(--muted)', cursor: 'pointer' }}>{p}</button>
        ))}
      </div>

      {pulling && (
        <div style={{ background: 'var(--rail)', border: '1px solid var(--hair-1)', borderRadius: 12,
                      padding: '12px 16px', marginBottom: 12 }}>
          <div style={{ fontSize: 13, color: 'var(--text-2)', marginBottom: 8 }}>
            {pulling} — {prog?.status ?? 'starting…'}{pct !== null ? ` ${pct}%` : ''}
          </div>
          <div style={{ height: 6, background: 'var(--hover)', borderRadius: 999, overflow: 'hidden' }}>
            <div style={{ height: '100%', width: `${pct ?? 3}%`, transition: 'width .3s',
                          background: 'linear-gradient(90deg,var(--send-a),var(--send-b))' }}/>
          </div>
        </div>
      )}
      {err && <div style={{ color: 'var(--grad-a)', fontSize: 12, marginBottom: 12 }}>{err}</div>}

      {local.map(m => (
        <div key={m} style={{ display: 'flex', alignItems: 'center', background: 'var(--rail)',
                              border: '1px solid var(--hair-1)', borderRadius: 10,
                              padding: '10px 14px', marginBottom: 8 }}>
          <span style={{ flex: 1, fontSize: 13.5, color: 'var(--text)' }}>{m}</span>
          <button onClick={() => remove(m)}
                  style={{ padding: '4px 10px', borderRadius: 8, fontSize: 12, cursor: 'pointer',
                           background: 'transparent', border: '1px solid #5b3333', color: '#e66767' }}>
            Delete
          </button>
        </div>
      ))}
      {local.length === 0 && !pulling && (
        <div style={{ color: 'var(--faint)', fontSize: 13 }}>
          No local models (is Ollama running?).
        </div>
      )}
    </>
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
        <ModelsSection/>
      </div>
    </div>
  )
}
