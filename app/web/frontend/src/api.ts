// Backend contracts (FastAPI on same origin / vite proxy in dev)
import { fetchEventSource } from '@microsoft/fetch-event-source'

export type Conversation = { id: string; title: string; updated_at: string }
export type Message = { role: string; content: string; created_at?: string }
export type ActivityEntry = { kind: string; text: string; ts?: string }
export type ModelsByProvider = Record<string, string[]>
export type Stats = {
  totals: { runs: number; success_rate: number; avg_ms: number; p95_ms: number;
            input_tokens: number; output_tokens: number; cost_usd: number }
  daily: { day: string; runs: number; cost: number; avg_ms: number }[]
  recent: { ts: string; model: string; ms: number; tokens: number; cost: number; ok: boolean }[]
}

const j = async <T,>(url: string): Promise<T> => {
  const r = await fetch(url)
  if (r.status === 401 || r.redirected) { window.location.href = '/login'; throw new Error('auth') }
  return r.json()
}

const postJson = async <T,>(url: string, body: unknown): Promise<T> => {
  const r = await fetch(url, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  })
  if (r.status === 401 || r.redirected) { window.location.href = '/login'; throw new Error('auth') }
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export const getConversations = () => j<Conversation[]>('/conversations')
export const getMessages = (id: string) => j<Message[]>('/conversations/' + id)
export const getActivity = (id: string) => j<ActivityEntry[]>('/conversations/' + id + '/activity')
export const getModels = () => j<ModelsByProvider>('/models')
export type SecretStatus = Record<string, boolean>
export const getSecrets = () => j<SecretStatus>('/secrets')
export const setSecret = (provider: string, key: string) =>
  postJson<{ ok: boolean }>('/secrets', { provider, key })
export const getGraph = () => j<{ nodes: never[]; links: never[] }>('/graph')
export const getStats = () => j<Stats>('/stats')

export type CalEvent = { id: number; title: string; start_ts: string; end_ts?: string | null;
                         location?: string | null; notes?: string | null }
export const getCalendar = () => j<CalEvent[]>('/calendar')
export const createEvent = (e: { title: string; start: string; end?: string | null;
                                 location?: string | null; notes?: string | null }) =>
  postJson<{ id: number }>('/calendar', e)
export const deleteEvent = async (id: number) => {
  const r = await fetch('/calendar/' + id, { method: 'DELETE' })
  if (r.status === 401 || r.redirected) { window.location.href = '/login'; throw new Error('auth') }
  return r.json() as Promise<{ ok: boolean }>
}
export const getStatus = () => j<{ graph: string; term_enabled: boolean }>('/status')

export type SkillInfo = { name: string; description: string; body?: string }
export type AgentInfo = { name: string; description: string; tools: string[] }
export type PendingTool = { name: string; code: string }
export const getSkills = () => j<{ live: SkillInfo[]; pending: SkillInfo[];
                                   agents: AgentInfo[]; pending_tools: PendingTool[] }>('/skills')
export const approveSkill = (name: string) =>
  postJson<{ ok: boolean }>(`/skills/${name}/approve`, {})
export const rejectSkill = (name: string) =>
  postJson<{ ok: boolean }>(`/skills/${name}/reject`, {})
export const approveTool = (name: string) =>
  postJson<{ ok: boolean }>(`/tools/${name}/approve`, {})
export const rejectTool = (name: string) =>
  postJson<{ ok: boolean }>(`/tools/${name}/reject`, {})

// ── local model management (Ollama) ──
export type PullProgress = { status?: string; completed?: number; total?: number; error?: string }
export function pullModel(name: string, onProgress: (p: PullProgress) => void,
                          onDone: () => void, onError: (e: string) => void) {
  return fetchEventSource('/models/pull', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
    openWhenHidden: true,
    onmessage(ev) {
      if (ev.event === 'progress') {
        const p: PullProgress = JSON.parse(ev.data)
        if (p.error) onError(p.error)
        else onProgress(p)
      } else if (ev.event === 'done') onDone()
    },
    onerror(err) { onError(String(err)); throw err },
  })
}
export const deleteModel = async (name: string) => {
  const r = await fetch('/models/' + name, { method: 'DELETE' })
  if (r.status === 401 || r.redirected) { window.location.href = '/login'; throw new Error('auth') }
  return r.json() as Promise<{ ok: boolean }>
}

export type StreamHandlers = {
  onConversation: (id: string) => void
  onToken: (t: string) => void
  onActivity: (a: ActivityEntry) => void
  onDone: () => void
  onError: (e: string) => void
  onPlan?: (plan: string[]) => void   // research mode: proposed sub-questions to approve
}

const sseHandlers = (h: StreamHandlers, signal: AbortSignal | undefined, body: unknown, url: string) => ({
  method: 'POST' as const,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
  signal,
  openWhenHidden: true,               // keep streaming when the tab is backgrounded
  onmessage(ev: { event: string; data: string }) {
    if (ev.event === 'conversation') h.onConversation(ev.data)
    else if (ev.event === 'activity') h.onActivity(JSON.parse(ev.data))
    else if (ev.event === 'plan') h.onPlan?.(JSON.parse(ev.data))
    else if (ev.event === 'done') h.onDone()
    else if (ev.data) h.onToken(JSON.parse(ev.data))
  },
  onerror(err: unknown) { h.onError(String(err)); throw err },  // no auto-retry storms
  _url: url,
})

// POST-based SSE with spec-correct parsing (handles \r\n, retries disabled)
export function streamChat(
  body: { message: string; conversation_id: string | null; model: string | null; provider: string | null; mode: string },
  h: StreamHandlers, signal?: AbortSignal,
) {
  const { _url, ...opts } = sseHandlers(h, signal, body, '/chat')
  return fetchEventSource(_url, opts)
}

// Resume a paused deep-research run with the approved (possibly edited) plan.
export function resumeResearch(
  body: { conversation_id: string; plan: string[]; model: string | null; provider: string | null },
  h: StreamHandlers, signal?: AbortSignal,
) {
  const { _url, ...opts } = sseHandlers(h, signal, body, '/chat/resume')
  return fetchEventSource(_url, opts)
}

export const relTime = (iso: string) => {
  const s = (Date.now() - new Date(iso).getTime()) / 1000
  if (isNaN(s)) return ''
  if (s < 60) return 'just now'
  if (s < 3600) return Math.floor(s / 60) + 'm ago'
  if (s < 86400) return Math.floor(s / 3600) + 'h ago'
  return Math.floor(s / 86400) + 'd ago'
}
