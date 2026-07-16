import { Suspense, lazy, useCallback, useEffect, useRef, useState } from 'react'
import Sidebar, { type View } from './components/Sidebar'
import ChatView from './components/ChatView'
import Composer from './components/Composer'
import StatsView from './components/StatsView'
import PlanApproval from './components/PlanApproval'

// heavy views load on demand (three.js / xterm stay out of the initial bundle)
const BrainView = lazy(() => import('./components/BrainView'))
const TerminalView = lazy(() => import('./components/TerminalView'))
const KeysView = lazy(() => import('./components/KeysView'))
const CalendarView = lazy(() => import('./components/CalendarView'))
const SkillsView = lazy(() => import('./components/SkillsView'))
const DataView = lazy(() => import('./components/DataView'))
import type { ActivityEntry, Conversation, Message, ModelsByProvider, StreamHandlers } from './api'
import { getActivity, getConversations, getMessages, getModels, getStatus, resumeResearch, streamChat } from './api'
import { ChevronDown } from './components/Icons'

export default function App() {
  const [view, setView] = useState<View>('chat')
  const [collapsed, setCollapsed] = useState(false)
  const [convs, setConvs] = useState<Conversation[]>([])
  const [convId, setConvId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [models, setModels] = useState<ModelsByProvider>({})
  const [streaming, setStreaming] = useState('')
  const [activity, setActivity] = useState<ActivityEntry[]>([])
  const [busy, setBusy] = useState(false)
  const [graphStatus, setGraphStatus] = useState('idle')
  const [termEnabled, setTermEnabled] = useState(false)
  const [plan, setPlan] = useState<string[] | null>(null)   // research: awaiting approval
  const researchCtx = useRef<{ model: string | null; provider: string | null }>({ model: null, provider: null })

  // rAF token batching: buffer stream tokens, flush once per frame
  const pendingRef = useRef('')
  const rafRef = useRef(0)
  const flush = useCallback(() => {
    rafRef.current = 0
    if (!pendingRef.current) return
    const chunk = pendingRef.current
    pendingRef.current = ''
    setStreaming(s => s + chunk)
  }, [])

  useEffect(() => {
    getConversations().then(setConvs).catch(console.error)
    getModels().then(setModels).catch(console.error)
    const pollStatus = () => {
      if (document.visibilityState === 'visible') getStatus().then(s => {
        setGraphStatus(s.graph)
        setTermEnabled(s.term_enabled)
      }).catch(() => {})
    }
    pollStatus()
    const t = window.setInterval(pollStatus, 10000)
    return () => window.clearInterval(t)
  }, [])

  // stable identities so React.memo(Sidebar) can actually skip re-renders
  // while a reply streams (App re-renders every animation frame during that)
  const openConv = useCallback(async (id: string) => {
    setConvId(id)
    setView('chat')
    const [msgs, act] = await Promise.all([getMessages(id), getActivity(id).catch(() => [])])
    setMessages(msgs)
    setActivity(act)
  }, [])

  const newChat = useCallback(() => {
    setConvId(null)
    setMessages([])
    setActivity([])
    setView('chat')
  }, [])

  const toggleCollapsed = useCallback(() => setCollapsed(c => !c), [])

  // shared streaming consumer: drives token batching + finalize for both a fresh
  // /chat turn and a /chat/resume research continuation.
  const consumeStream = async (start: (h: StreamHandlers) => Promise<unknown>) => {
    setStreaming('')
    let acc = ''  // authoritative copy of the reply
    try {
      await start({
        onConversation: id => setConvId(id),
        onToken: t => {
          acc += t
          pendingRef.current += t
          if (!rafRef.current) rafRef.current = requestAnimationFrame(flush)
        },
        onActivity: a => setActivity(l => [...l, a]),
        onPlan: p => setPlan(p),   // research: surface the plan for approval
        onDone: () => {},          // keep the turn's log; it persists per-conversation
        onError: e => setActivity(l => [...l, { kind: 'error', text: 'error: ' + e }]),
      })
    } catch { /* onError already surfaced it */ }
    if (rafRef.current) { cancelAnimationFrame(rafRef.current); rafRef.current = 0 }
    pendingRef.current = ''
    setStreaming('')
    if (acc) setMessages(ms => [...ms, { role: 'assistant', content: acc }])
  }

  const send = async (msg: string, provider: string | null, model: string | null, mode: string) => {
    setBusy(true)
    setPlan(null)
    setMessages(ms => [...ms, { role: 'user', content: msg }])
    researchCtx.current = { model, provider }   // remembered for a research resume
    const isNew = !convId
    await consumeStream(h => streamChat({ message: msg, conversation_id: convId, model, provider, mode }, h))
    setBusy(false)
    if (isNew) getConversations().then(setConvs).catch(console.error)
  }

  // Data tab "Analyze": jump to chat and hand the file to the data-analyst
  const analyzeFile = (path: string) => {
    setView('chat')
    void send(
      `Use the data-analyst subagent to analyze ${path}: profile the data, ` +
      'clean if needed, and report the key findings with numbers.',
      null, null, 'agent')
  }

  const approvePlan = async (edited: string[]) => {
    if (!convId) return
    setBusy(true)
    setPlan(null)
    const { model, provider } = researchCtx.current
    await consumeStream(h => resumeResearch({ conversation_id: convId, plan: edited, model, provider }, h))
    setBusy(false)
  }

  const title = convId ? (convs.find(c => c.id === convId)?.title ?? 'Chat') : 'New Chat'

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column',
                  background: 'var(--shell)', overflow: 'hidden' }}>
      {/* macOS-style titlebar */}
      <div style={{ height: 52, flex: '0 0 52px', background: 'var(--rail)', display: 'flex',
                    alignItems: 'center', gap: 18, padding: '0 22px',
                    borderBottom: '1px solid var(--hair-1)' }}>
        <div style={{ display: 'flex', gap: 9, alignItems: 'center' }}>
          <span style={{ width: 13, height: 13, borderRadius: '50%', background: '#ec6a5e' }}/>
          <span style={{ width: 13, height: 13, borderRadius: '50%', background: '#f4bf4f' }}/>
          <span style={{ width: 13, height: 13, borderRadius: '50%', background: '#61c554' }}/>
        </div>
        <div style={{ flex: 1, height: 30, background: 'var(--hover)', borderRadius: 8,
                      border: '1px solid #23272e', display: 'flex', alignItems: 'center',
                      justifyContent: 'center', color: 'var(--faint)', fontSize: 12 }}>
          argus · localhost:8000
        </div>
      </div>

      <div style={{ flex: 1, display: 'flex', minHeight: 0 }}>
        <Sidebar convs={convs} activeConv={convId} view={view} graphStatus={graphStatus}
                 collapsed={collapsed} termEnabled={termEnabled} onToggle={toggleCollapsed}
                 onNewChat={newChat} onOpenConv={openConv} onView={setView}/>

        <main style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0,
                       background: 'var(--shell)' }}>
          {view === 'chat' && (
            <>
              <div style={{ height: 64, flex: '0 0 64px', display: 'flex',
                            alignItems: 'center', justifyContent: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text-2)',
                              fontSize: 14, padding: '6px 12px', borderRadius: 8 }}>
                  <span>{title}</span>
                  <ChevronDown size={14}/>
                </div>
              </div>
              <ChatView messages={messages} streaming={streaming} activity={activity}/>
              {plan && <PlanApproval plan={plan} disabled={busy} onApprove={approvePlan}/>}
              <Composer models={models} disabled={busy} onSend={send} termEnabled={termEnabled}
                        onTerminal={() => setView('terminal')}/>
            </>
          )}
          <Suspense fallback={<div style={{ padding: 40, color: 'var(--muted)' }}>loading ...</div>}>
            {view === 'graph' && <BrainView/>}
            {view === 'calendar' && <CalendarView/>}
            {view === 'skills' && <SkillsView/>}
            {view === 'data' && <DataView onAnalyze={analyzeFile}/>}
            {view === 'stats' && <StatsView/>}
            {view === 'settings' && <KeysView/>}
            {view === 'terminal' && termEnabled && <TerminalView/>}
          </Suspense>
        </main>
      </div>
    </div>
  )
}
