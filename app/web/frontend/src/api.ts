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

export const getConversations = () => j<Conversation[]>('/conversations')
export const getMessages = (id: string) => j<Message[]>('/conversations/' + id)
export const getActivity = (id: string) => j<ActivityEntry[]>('/conversations/' + id + '/activity')
export const getModels = () => j<ModelsByProvider>('/models')
export const getGraph = () => j<{ nodes: never[]; links: never[] }>('/graph')
export const getStats = () => j<Stats>('/stats')
export const getStatus = () => j<{ graph: string; term_enabled: boolean }>('/status')

export type StreamHandlers = {
  onConversation: (id: string) => void
  onToken: (t: string) => void
  onActivity: (a: ActivityEntry) => void
  onDone: () => void
  onError: (e: string) => void
}

// POST-based SSE with spec-correct parsing (handles \r\n, retries disabled)
export function streamChat(
  body: { message: string; conversation_id: string | null; model: string | null; provider: string | null; mode: string },
  h: StreamHandlers, signal?: AbortSignal,
) {
  return fetchEventSource('/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
    openWhenHidden: true,             // keep streaming when the tab is backgrounded
    onmessage(ev) {
      if (ev.event === 'conversation') h.onConversation(ev.data)
      else if (ev.event === 'activity') h.onActivity(JSON.parse(ev.data))
      else if (ev.event === 'done') h.onDone()
      else if (ev.data) h.onToken(JSON.parse(ev.data))
    },
    onerror(err) { h.onError(String(err)); throw err },  // no auto-retry storms
  })
}

export const relTime = (iso: string) => {
  const s = (Date.now() - new Date(iso).getTime()) / 1000
  if (isNaN(s)) return ''
  if (s < 60) return 'just now'
  if (s < 3600) return Math.floor(s / 60) + 'm ago'
  if (s < 86400) return Math.floor(s / 3600) + 'h ago'
  return Math.floor(s / 86400) + 'd ago'
}
