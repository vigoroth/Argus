import { useEffect, useRef } from 'react'
import type { ActivityEntry, Message } from '../api'

export default function ChatView({ messages, streaming, activity }: {
  messages: Message[]; streaming: string; activity: ActivityEntry[]
}) {
  const boxRef = useRef<HTMLDivElement>(null)
  const stickRef = useRef(true)
  const logRef = useRef<HTMLDivElement>(null)

  // stick to bottom only if the reader is already there
  useEffect(() => {
    const el = boxRef.current
    if (el && stickRef.current) el.scrollTop = el.scrollHeight
  }, [messages, streaming])

  // activity log always follows the newest entry
  useEffect(() => {
    const el = logRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [activity])

  const empty = messages.length === 0 && !streaming

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
      {empty ? (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center',
                      justifyContent: 'center', gap: 18, padding: '0 24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <span style={{ fontSize: 42 }}>⛵</span>
            <span style={{ fontSize: 54, fontWeight: 700, letterSpacing: 1,
                           background: 'linear-gradient(180deg,var(--grad-a),var(--grad-b))',
                           WebkitBackgroundClip: 'text', backgroundClip: 'text',
                           color: 'transparent' }}>Argus</span>
          </div>
          <div style={{ color: 'var(--muted)', fontSize: 15, letterSpacing: .3 }}>Yours for the voyage.</div>
          <div style={{ color: 'var(--faint)', fontSize: 13, textAlign: 'center', maxWidth: 420,
                        lineHeight: 1.7, marginTop: 14 }}>
            Tip: the Brain tab shows the knowledge graph of your conversations.
          </div>
        </div>
      ) : (
        <div ref={boxRef}
             onScroll={e => {
               const el = e.currentTarget
               stickRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 60
             }}
             style={{ flex: 1, overflowY: 'auto', padding: '24px 36px', minHeight: 0 }}>
          <div style={{ maxWidth: 900, margin: '0 auto' }}>
            {messages.map((m, i) => (
              <div key={i} title={m.created_at ? m.created_at.slice(0, 16).replace('T', ' ') : undefined}
                   style={{ margin: '14px 0', padding: '12px 16px', borderRadius: 12,
                            whiteSpace: 'pre-wrap', lineHeight: 1.6, fontSize: 14,
                            background: m.role === 'user' ? 'var(--pill-on)' : 'var(--rail)',
                            border: '1px solid ' + (m.role === 'user' ? 'var(--pill-br)' : 'var(--hair-1)'),
                            marginLeft: m.role === 'user' ? '4rem' : 0,
                            marginRight: m.role === 'user' ? 0 : '4rem' }}>
                {m.content}
              </div>
            ))}
            {streaming && (
              <div style={{ margin: '14px 4rem 14px 0', padding: '12px 16px', borderRadius: 12,
                            whiteSpace: 'pre-wrap', lineHeight: 1.6, fontSize: 14,
                            background: 'var(--rail)', border: '1px solid var(--hair-1)' }}>
                {streaming}<span style={{ color: 'var(--violet)' }}>▋</span>
              </div>
            )}
          </div>
        </div>
      )}
      {activity.length > 0 && (
        <div ref={logRef}
             style={{ maxHeight: 116, overflowY: 'auto', padding: '6px 36px 8px',
                      maxWidth: 1030, margin: '0 auto', width: '100%' }}>
          {activity.map((a, i) => (
            <div key={i}
                 style={{ display: 'flex', gap: 8, alignItems: 'baseline',
                          color: a.kind === 'error' ? 'var(--grad-a)' : 'var(--faint)',
                          fontSize: 12, fontFamily: 'ui-monospace, SFMono-Regular, monospace',
                          lineHeight: 1.7, whiteSpace: 'nowrap', overflow: 'hidden',
                          textOverflow: 'ellipsis' }}>
              <span style={{ opacity: .7 }}>⚙</span>
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{a.text}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
