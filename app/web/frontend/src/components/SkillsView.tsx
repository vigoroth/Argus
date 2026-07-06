import { useEffect, useState } from 'react'
import { getSkills, approveSkill, rejectSkill, approveTool, rejectTool,
         type SkillInfo, type AgentInfo, type PendingTool } from '../api'

// Skills tab: live skill index, subagents, and the approval queues for
// agent-drafted skills (instructions) and tools (code). Approving is the
// "capability firewall" — nothing the agent writes goes live until reviewed here.
export default function SkillsView() {
  const [live, setLive] = useState<SkillInfo[]>([])
  const [pending, setPending] = useState<SkillInfo[]>([])
  const [agents, setAgents] = useState<AgentInfo[]>([])
  const [pendingTools, setPendingTools] = useState<PendingTool[]>([])
  const [busy, setBusy] = useState<string | null>(null)

  const load = () => getSkills().then(r => {
    setLive(r.live); setPending(r.pending)
    setAgents(r.agents ?? []); setPendingTools(r.pending_tools ?? [])
  }).catch(console.error)
  useEffect(() => { load() }, [])

  const act = async (name: string, fn: (n: string) => Promise<unknown>) => {
    setBusy(name)
    try { await fn(name) } catch (e) { console.error(e) }
    setBusy(null)
    load()
  }

  const btn: React.CSSProperties = { background: 'var(--btn-bg)', border: '1px solid var(--hair-2)',
    borderRadius: 8, color: 'var(--text-2)', cursor: 'pointer', padding: '6px 12px', fontSize: 13 }
  const card: React.CSSProperties = { background: 'var(--rail)', border: '1px solid var(--hair-1)',
    borderRadius: 10, padding: '14px 16px', marginBottom: 10 }

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: '20px 28px', minHeight: 0 }}>
      <h2 style={{ margin: '0 0 4px', fontSize: 20, color: 'var(--text)' }}>Skills</h2>
      <div style={{ color: 'var(--faint)', fontSize: 12.5, marginBottom: 18 }}>
        Loadable capabilities. The agent sees one line per skill and pulls the full
        instructions on demand. Drafts it writes for itself wait below for your approval.
      </div>

      {pending.length > 0 && (
        <>
          <h3 style={{ fontSize: 14, color: 'var(--violet)', margin: '0 0 10px' }}>
            Pending approval ({pending.length})
          </h3>
          {pending.map(s => (
            <div key={s.name} style={{ ...card, borderColor: 'var(--pill-br)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                <span style={{ color: 'var(--text)', fontWeight: 600, fontSize: 14.5 }}>{s.name}</span>
                <span style={{ color: 'var(--muted)', fontSize: 12.5, flex: 1 }}>{s.description}</span>
                <button style={{ ...btn, color: '#7ccb6e', borderColor: '#3a5b33' }}
                        disabled={busy === s.name}
                        onClick={() => act(s.name, approveSkill)}>Approve</button>
                <button style={{ ...btn, color: '#e66767', borderColor: '#5b3333' }}
                        disabled={busy === s.name}
                        onClick={() => act(s.name, rejectSkill)}>Reject</button>
              </div>
              <pre style={{ margin: 0, padding: '10px 12px', background: 'var(--shell)',
                            border: '1px solid var(--hair-1)', borderRadius: 8, fontSize: 12,
                            color: 'var(--text-2)', whiteSpace: 'pre-wrap', maxHeight: 260,
                            overflowY: 'auto' }}>{s.body}</pre>
            </div>
          ))}
          <div style={{ height: 14 }}/>
        </>
      )}

      <h3 style={{ fontSize: 14, color: 'var(--blue)', margin: '0 0 10px' }}>
        Live ({live.length})
      </h3>
      {live.map(s => (
        <div key={s.name} style={card}>
          <span style={{ color: 'var(--text)', fontWeight: 600, fontSize: 14.5,
                         marginRight: 10 }}>{s.name}</span>
          <span style={{ color: 'var(--muted)', fontSize: 12.5 }}>{s.description}</span>
        </div>
      ))}
      {live.length === 0 && (
        <div style={{ color: 'var(--faint)', fontSize: 13 }}>No skills yet.</div>
      )}

      {pendingTools.length > 0 && (
        <>
          <div style={{ height: 18 }}/>
          <h3 style={{ fontSize: 14, color: 'var(--violet)', margin: '0 0 4px' }}>
            Pending tools — code review ({pendingTools.length})
          </h3>
          <div style={{ color: 'var(--faint)', fontSize: 12, marginBottom: 10 }}>
            Agent-written Python. Read it before approving — approved tools execute with
            the app's permissions.
          </div>
          {pendingTools.map(t => (
            <div key={t.name} style={{ ...card, borderColor: 'var(--pill-br)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                <span style={{ color: 'var(--text)', fontWeight: 600, fontSize: 14.5, flex: 1 }}>{t.name}</span>
                <button style={{ ...btn, color: '#7ccb6e', borderColor: '#3a5b33' }}
                        disabled={busy === t.name}
                        onClick={() => act(t.name, approveTool)}>Approve</button>
                <button style={{ ...btn, color: '#e66767', borderColor: '#5b3333' }}
                        disabled={busy === t.name}
                        onClick={() => act(t.name, rejectTool)}>Reject</button>
              </div>
              <pre style={{ margin: 0, padding: '10px 12px', background: 'var(--shell)',
                            border: '1px solid var(--hair-1)', borderRadius: 8, fontSize: 12,
                            color: 'var(--text-2)', whiteSpace: 'pre-wrap', maxHeight: 320,
                            overflowY: 'auto' }}>{t.code}</pre>
            </div>
          ))}
        </>
      )}

      <div style={{ height: 18 }}/>
      <h3 style={{ fontSize: 14, color: 'var(--blue)', margin: '0 0 10px' }}>
        Subagents ({agents.length})
      </h3>
      {agents.map(a => (
        <div key={a.name} style={card}>
          <span style={{ color: 'var(--text)', fontWeight: 600, fontSize: 14.5,
                         marginRight: 10 }}>{a.name}</span>
          <span style={{ color: 'var(--muted)', fontSize: 12.5 }}>{a.description}</span>
          <div style={{ color: 'var(--faint)', fontSize: 11.5, marginTop: 4 }}>
            tools: {a.tools.join(', ') || '—'}
          </div>
        </div>
      ))}
      {agents.length === 0 && (
        <div style={{ color: 'var(--faint)', fontSize: 13 }}>No subagents defined.</div>
      )}
    </div>
  )
}
