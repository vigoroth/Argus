import { useEffect, useState } from 'react'
import {
  adoptBrainEdits, approveBrainProposal, captureBrain, getBrainAudit, getBrainNote,
  getBrainStages, getBrainStatus, migrateBrainMemory, rebuildBrainIndex,
  rejectBrainProposal, searchBrain, validateBrain,
  type BrainAudit, type BrainNote, type BrainStatus,
} from '../api'

const STAGES = ['inbox', 'projects', 'output', 'wiki']

export default function BrainView() {
  const [status, setStatus] = useState<BrainStatus | null>(null)
  const [stages, setStages] = useState<Record<string, BrainNote[]>>({})
  const [selected, setSelected] = useState<BrainNote | null>(null)
  const [q, setQ] = useState('')
  const [results, setResults] = useState<BrainNote[] | null>(null)
  const [capture, setCapture] = useState('')
  const [message, setMessage] = useState('')
  const [audit, setAudit] = useState<BrainAudit | null>(null)
  const [showAudit, setShowAudit] = useState(false)

  const load = async () => {
    const [s, notes] = await Promise.all([getBrainStatus(), getBrainStages()])
    setStatus(s); setStages(notes)
  }
  const loadAudit = async () => setAudit(await getBrainAudit())
  useEffect(() => { void load() }, [])

  const openNote = async (note: BrainNote) => {
    const [stage, filename] = note.path.split('/')
    setSelected(await getBrainNote(stage, filename))
  }

  const search = async () => {
    setResults(q.trim() ? await searchBrain(q.trim()) : null)
  }

  const addCapture = async () => {
    if (!capture.trim()) return
    try {
      const result = await captureBrain(capture.trim())
      setMessage(result.note ? `Captured ${result.note}` : 'Nothing captured.')
      setCapture('')
      await load()
    } catch (e) { setMessage(String(e)) }
  }

  const card: React.CSSProperties = {
    background: 'var(--rail)', border: '1px solid var(--hair-1)',
    borderRadius: 10, padding: '10px 12px', cursor: 'pointer',
  }

  return (
    <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column',
                  padding: '18px 22px', gap: 12, overflow: 'hidden' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{ flex: 1 }}>
          <h2 style={{ margin: 0, fontSize: 20 }}>Second Brain</h2>
          <div style={{ color: 'var(--faint)', fontSize: 12, marginTop: 3 }}>
            Canonical Markdown · Git-backed · Obsidian-compatible
          </div>
        </div>
        {status?.obsidian_uri && (
          <a href={status.obsidian_uri}
             style={{ color: 'var(--violet)', fontSize: 12.5, textDecoration: 'none',
                      border: '1px solid var(--pill-br)', borderRadius: 8, padding: '7px 11px' }}>
            Open in Obsidian
          </a>
        )}
        <button onClick={async () => {
                  try { setMessage(JSON.stringify(await adoptBrainEdits())); await load() }
                  catch (e) { setMessage(String(e)) }
                }}
                style={{ background: 'var(--btn-bg)', color: 'var(--text-2)',
                         border: '1px solid var(--hair-2)', borderRadius: 8, padding: '7px 11px' }}>
          Adopt edits
        </button>
        <button onClick={async () => {
                  try { setMessage(JSON.stringify(await migrateBrainMemory())); await load() }
                  catch (e) { setMessage(String(e)) }
                }}
                style={{ background: 'var(--btn-bg)', color: 'var(--text-2)',
                         border: '1px solid var(--hair-2)', borderRadius: 8, padding: '7px 11px' }}>
          Migrate memory
        </button>
        <button onClick={async () => {
                  const next = !showAudit; setShowAudit(next)
                  if (next) await loadAudit()
                }}
                style={{ background: 'var(--btn-bg)', color: 'var(--text-2)',
                         border: '1px solid var(--hair-2)', borderRadius: 8, padding: '7px 11px' }}>
          {showAudit ? 'Notes' : 'Audit'}
        </button>
      </div>

      {status && (
        <div style={{ ...card, cursor: 'default', display: 'flex', gap: 14,
                      color: 'var(--muted)', fontSize: 12 }}>
          <span style={{ color: status.valid ? 'var(--ok)' : 'var(--crit)' }}>
            {status.valid ? '✓ valid' : '✕ invalid'}
          </span>
          <span>commit {status.commit?.slice(0, 10) ?? 'none'}</span>
          <span>{status.dirty_paths.length ? `${status.dirty_paths.length} external edits` : 'clean'}</span>
          <span>capture {status.auto_capture ? 'on' : 'off'}</span>
          <span>context {status.context ? 'on' : 'off'}</span>
          <span>watcher {status.watcher?.running ? 'on' : 'off'}</span>
          {status.watcher?.last_error && (
            <span style={{ color: 'var(--crit)' }}>{status.watcher.last_error}</span>
          )}
          {!status.valid && <span>{status.validation_errors.join(' · ')}</span>}
        </div>
      )}

      <div style={{ display: 'flex', gap: 8 }}>
        <input value={q} onChange={e => setQ(e.target.value)}
               onKeyDown={e => { if (e.key === 'Enter') void search() }}
               placeholder="Search canonical memory…"
               style={{ flex: 1, background: 'var(--rail)', color: 'var(--text)',
                        border: '1px solid var(--hair-2)', borderRadius: 8, padding: '8px 10px' }}/>
        <button onClick={() => void search()}
                style={{ background: 'var(--pill-on)', color: 'var(--pill-fg)',
                         border: '1px solid var(--pill-br)', borderRadius: 8, padding: '7px 13px' }}>
          Search
        </button>
      </div>

      <div style={{ display: 'flex', gap: 8 }}>
        <input value={capture} onChange={e => setCapture(e.target.value)}
               placeholder="Capture a durable fact or idea…"
               style={{ flex: 1, background: 'var(--rail)', color: 'var(--text)',
                        border: '1px solid var(--hair-2)', borderRadius: 8, padding: '8px 10px' }}/>
        <button onClick={() => void addCapture()}
                style={{ background: 'var(--btn-bg)', color: 'var(--text-2)',
                         border: '1px solid var(--hair-2)', borderRadius: 8, padding: '7px 13px' }}>
          Capture
        </button>
      </div>
      {message && <div style={{ color: 'var(--faint)', fontSize: 11.5 }}>{message}</div>}

      {showAudit ? (
        <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', display: 'grid', gap: 10 }}>
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={async () => {
                      const r = await validateBrain()
                      setMessage(r.valid ? 'Vault validation passed.' : r.errors.join(' · '))
                    }}>Validate vault</button>
            <button onClick={async () => {
                      const r = await rebuildBrainIndex()
                      setMessage(`Rebuilt index: ${r.indexed} notes`)
                    }}>Rebuild index</button>
          </div>
          <section>
            <h3>Pending proposals</h3>
            {(audit?.proposals.filter(p => p.state === 'pending') ?? []).map(p => (
              <div key={p.proposal_id} style={{ ...card, cursor: 'default', marginBottom: 8 }}>
                <div><strong>{p.operation}</strong> · {p.proposal_id}</div>
                <div style={{ color: 'var(--faint)', fontSize: 11 }}>{p.payload.paths.join(' · ')}</div>
                <pre style={{ maxHeight: 180, overflow: 'auto', whiteSpace: 'pre-wrap',
                              fontSize: 10.5 }}>{p.payload.patch}</pre>
                <div style={{ display: 'flex', gap: 7 }}>
                  <button onClick={async () => {
                            await approveBrainProposal(p.proposal_id, p.diff_hash)
                            setMessage(`Approved and executed ${p.proposal_id}`)
                            await Promise.all([load(), loadAudit()])
                          }}>Approve exact diff</button>
                  <button onClick={async () => {
                            await rejectBrainProposal(p.proposal_id, 'Rejected in Brain audit UI')
                            await loadAudit()
                          }}>Reject</button>
                </div>
              </div>
            ))}
          </section>
          <section>
            <h3>Transactions</h3>
            {(audit?.transactions ?? []).map(t => (
              <div key={t.commit} style={{ fontSize: 11.5, marginBottom: 5 }}>
                {t.commit.slice(0, 10)} · {t.subject}
              </div>
            ))}
          </section>
          <section>
            <h3>Remote disclosures</h3>
            {(audit?.disclosures ?? []).map(d => (
              <div key={d.id} style={{ fontSize: 11.5 }}>{d.ts} · {d.provider}/{d.model ?? ''}</div>
            ))}
          </section>
          <section>
            <h3>Rejected captures</h3>
            {(audit?.rejections ?? []).map(r => (
              <div key={r.id} style={{ fontSize: 11.5 }}>{r.ts} · {r.source} · {r.reason}</div>
            ))}
          </section>
        </div>
      ) : <div style={{ flex: 1, minHeight: 0, display: 'grid',
                    gridTemplateColumns: selected ? '1fr 1.2fr' : '1fr', gap: 12 }}>
        <div style={{ minHeight: 0, overflowY: 'auto' }}>
          {results ? (
            <>
              <h3 style={{ fontSize: 13, color: 'var(--violet)' }}>Search results</h3>
              {results.map(n => (
                <div key={n.path} style={{ ...card, marginBottom: 7 }} onClick={() => void openNote(n)}>
                  <div style={{ fontSize: 13.5 }}>{n.title}</div>
                  <div style={{ color: 'var(--faint)', fontSize: 11 }}>{n.stage} · {n.path}</div>
                </div>
              ))}
            </>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2,minmax(0,1fr))', gap: 10 }}>
              {STAGES.map(stage => (
                <section key={stage}>
                  <h3 style={{ fontSize: 13, color: stage === 'wiki' ? 'var(--violet)' : 'var(--blue)',
                               textTransform: 'capitalize' }}>
                    {stage} ({stages[stage]?.length ?? 0})
                  </h3>
                  {(stages[stage] ?? []).map(n => (
                    <div key={n.path} style={{ ...card, marginBottom: 7 }}
                         onClick={() => void openNote(n)}>
                      <div style={{ fontSize: 13 }}>{n.title}</div>
                      <div style={{ color: 'var(--faint)', fontSize: 10.5 }}>{n.path}</div>
                    </div>
                  ))}
                </section>
              ))}
            </div>
          )}
        </div>

        {selected && (
          <article style={{ ...card, cursor: 'default', overflowY: 'auto', minHeight: 0 }}>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 10 }}>
              <strong style={{ flex: 1 }}>{selected.title}</strong>
              {selected.obsidian_uri && <a href={selected.obsidian_uri}
                style={{ color: 'var(--violet)', fontSize: 11.5 }}>Obsidian</a>}
              <button onClick={() => setSelected(null)}
                      style={{ background: 'transparent', border: 0, color: 'var(--muted)' }}>×</button>
            </div>
            <div style={{ color: 'var(--faint)', fontSize: 10.5, marginBottom: 10 }}>
              {selected.path} · sha256 {selected.sha256.slice(0, 12)}
            </div>
            <pre style={{ whiteSpace: 'pre-wrap', margin: 0, fontSize: 12.5,
                          lineHeight: 1.55, color: 'var(--text-2)' }}>{selected.body}</pre>
          </article>
        )}
      </div>}
    </div>
  )
}
