import { memo, useMemo, useState } from 'react'
import type { Conversation } from '../api'
import { relTime } from '../api'
import { Plus, Search, ChatBubble, Globe, Bars, Term, Bot, Key, Calendar, Zap, Menu, ChevronDown, ChevronRight } from './Icons'

export type View = 'chat' | 'graph' | 'stats' | 'terminal' | 'claude' | 'settings' | 'calendar' | 'skills'

const row: React.CSSProperties = {
  display: 'flex', alignItems: 'center', gap: 13, padding: '9px 11px',
  borderRadius: 8, cursor: 'pointer', fontSize: 14.5, userSelect: 'none',
}

function NavRow({ color, icon, label, right, onClick, active }: {
  color: string; icon: React.ReactNode; label: string; right?: React.ReactNode
  onClick?: () => void; active?: boolean
}) {
  const [hov, setHov] = useState(false)
  return (
    <div style={{ ...row, color, background: hov || active ? 'var(--hover)' : 'transparent' }}
         onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)} onClick={onClick}>
      {icon}<span style={{ flex: 1 }}>{label}</span>{right}
    </div>
  )
}

function Sidebar({ convs, activeConv, view, graphStatus, collapsed, termEnabled,
                    onToggle, onNewChat, onOpenConv, onView }: {
  convs: Conversation[]; activeConv: string | null; view: View; graphStatus: string
  collapsed: boolean; termEnabled: boolean; onToggle: () => void; onNewChat: () => void
  onOpenConv: (id: string) => void; onView: (v: View) => void
}) {
  const [q, setQ] = useState('')
  const [searching, setSearching] = useState(false)
  const [chatsOpen, setChatsOpen] = useState(true)
  // App re-renders this component every animation frame while a reply streams;
  // avoid re-filtering the conversation list on frames where the query/list didn't change
  const shown = useMemo(
    () => q ? convs.filter(c => c.title.toLowerCase().includes(q.toLowerCase())) : convs,
    [q, convs],
  )

  if (collapsed) return (
    <aside style={{ width: 54, flex: '0 0 54px', background: 'var(--rail)',
                    borderRight: '1px solid var(--hair-1)', padding: '20px 0',
                    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
      <div style={{ cursor: 'pointer', color: 'var(--violet)', padding: 8 }} onClick={onToggle}><Menu size={20}/></div>
    </aside>
  )

  return (
    <aside style={{ width: 316, flex: '0 0 316px', background: 'var(--rail)',
                    borderRight: '1px solid var(--hair-1)', display: 'flex',
                    flexDirection: 'column', padding: '20px 0', minHeight: 0 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '4px 22px 22px' }}>
        <span style={{ cursor: 'pointer', color: 'var(--violet)' }} onClick={onToggle}><Menu size={22}/></span>
        <span style={{ color: 'var(--violet)', fontWeight: 700, fontSize: 16, letterSpacing: .5 }}>Argus</span>
      </div>

      <nav style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column',
                    gap: 2, padding: '0 12px', minHeight: 0 }}>
        {/* primary — violet */}
        <NavRow color="var(--violet)" icon={<Plus/>} label="New Chat" onClick={onNewChat}/>
        <NavRow color="var(--violet)" icon={<Search/>} label="Search"
                onClick={() => { setSearching(s => !s); setQ('') }}/>
        {searching && (
          <input autoFocus value={q} onChange={e => setQ(e.target.value)}
                 placeholder="filter chats ..."
                 style={{ margin: '2px 11px 6px', padding: '7px 10px', background: 'var(--hover)',
                          border: '1px solid var(--hair-2)', borderRadius: 8, color: 'var(--text)',
                          fontSize: 13, outline: 'none' }}/>
        )}
        <NavRow color="var(--violet)" icon={<ChatBubble/>} label="Chats"
                right={chatsOpen ? <ChevronDown size={14} color="var(--violet-2)"/>
                                 : <ChevronRight size={14} color="var(--violet-2)"/>}
                onClick={() => setChatsOpen(o => !o)}/>
        {chatsOpen && shown.map(c => (
          <div key={c.id} onClick={() => onOpenConv(c.id)}
               style={{ padding: '5px 11px 5px 42px', borderRadius: 8, cursor: 'pointer',
                        color: c.id === activeConv ? 'var(--text-2)' : 'var(--muted)',
                        background: c.id === activeConv ? 'var(--hover)' : 'transparent',
                        fontSize: 12.8, overflow: 'hidden' }}>
            <div style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{c.title}</div>
            <div style={{ fontSize: 10.5, color: 'var(--faint)' }}>{relTime(c.updated_at)}</div>
          </div>
        ))}

        <div style={{ height: 10 }}/>

        {/* secondary — blue */}
        <NavRow color="var(--blue)" icon={<Globe/>} label="Brain" active={view === 'graph'}
                onClick={() => onView('graph')}
                right={<span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ color: 'var(--ph)', fontSize: 12.5 }}>{graphStatus}</span>
                  <span style={{ width: 8, height: 8, borderRadius: '50%',
                                 background: graphStatus === 'building' ? '#f4bf4f' : 'var(--green)',
                                 boxShadow: `0 0 6px ${graphStatus === 'building' ? '#f4bf4f88' : '#5fb84f88'}` }}/>
                </span>}/>
        <NavRow color="var(--blue)" icon={<Calendar/>} label="Calendar" active={view === 'calendar'}
                onClick={() => onView('calendar')}/>
        <NavRow color="var(--blue)" icon={<Zap/>} label="Skills" active={view === 'skills'}
                onClick={() => onView('skills')}/>
        <NavRow color="var(--blue)" icon={<Bars/>} label="Stats" active={view === 'stats'}
                onClick={() => onView('stats')}/>
        <NavRow color="var(--blue)" icon={<Key/>} label="API Keys" active={view === 'settings'}
                onClick={() => onView('settings')}/>
        {termEnabled && (
          <NavRow color="var(--blue)" icon={<Term/>} label="Terminal" active={view === 'terminal'}
                  onClick={() => onView('terminal')}/>
        )}
        {termEnabled && (
          <NavRow color="var(--violet)" icon={<Bot/>} label="Claude Code" active={view === 'claude'}
                  onClick={() => onView('claude')}/>
        )}
      </nav>
    </aside>
  )
}

export default memo(Sidebar)
