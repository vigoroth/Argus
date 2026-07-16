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
export type BrainStatus = {
  enabled: boolean; path: string; exists: boolean; git: boolean; commit: string | null
  dirty_paths: string[]; valid: boolean; validation_errors: string[]
  auto_capture: boolean; context: boolean; obsidian_uri: string | null
  watcher?: { running: boolean; last_event: string | null; last_commit: string | null;
              last_error: string | null }
}
export type BrainNote = {
  path: string; stage: string; name?: string; title: string; sha256: string
  body?: string; excerpt?: string; wikilink?: string; obsidian_uri?: string
}
export type BrainProposal = {
  proposal_id: string; operation: string; state: string; diff_hash: string
  created_at: string; expires_on: string
  payload: { paths: string[]; patch: string; provenance: Record<string, string>[] }
}
export type BrainAudit = {
  transactions: { commit: string; timestamp: string; subject: string }[]
  proposals: BrainProposal[]
  disclosures: { id: number; ts: string; provider: string; model?: string; paths: string }[]
  rejections: { id: number; ts: string; source: string; reason: string }[]
}
export const getBrainStatus = () => j<BrainStatus>('/brain/status')
export const getBrainStages = () => j<Record<string, BrainNote[]>>('/brain/stages')
export const getBrainNote = (stage: string, name: string) =>
  j<BrainNote>(`/brain/notes/${encodeURIComponent(stage)}/${encodeURIComponent(name)}`)
export const searchBrain = (q: string) =>
  j<BrainNote[]>('/brain/search?q=' + encodeURIComponent(q))
export const captureBrain = (material: string) =>
  postJson<{ note?: string; captured?: boolean }>('/brain/capture', { material })
export const adoptBrainEdits = () => postJson<Record<string, unknown>>('/brain/adopt', {})
export const migrateBrainMemory = () => postJson<Record<string, unknown>>('/brain/migrate', {})
export const getBrainAudit = () => j<BrainAudit>('/brain/audit')
export const approveBrainProposal = (id: string, diff_hash: string) =>
  postJson<Record<string, unknown>>(`/brain/proposals/${encodeURIComponent(id)}/approve`, { diff_hash })
export const rejectBrainProposal = (id: string, reason: string) =>
  postJson<BrainProposal>(`/brain/proposals/${encodeURIComponent(id)}/reject`, { reason })
export const rebuildBrainIndex = () => postJson<{ indexed: number }>('/brain/rebuild-index', {})
export const validateBrain = () => postJson<{ valid: boolean; errors: string[] }>('/brain/validate', {})
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
// ── uploads for the data-analyst ──
export type UploadInfo = { name: string; size: number; mtime: number }
export const getUploads = () => j<UploadInfo[]>('/uploads')
export const uploadFile = async (file: File) => {
  const fd = new FormData()
  fd.append('file', file)
  const r = await fetch('/upload', { method: 'POST', body: fd })
  if (r.status === 401 || r.redirected) { window.location.href = '/login'; throw new Error('auth') }
  if (!r.ok) throw new Error(await r.text())
  return r.json() as Promise<{ name: string; size: number; path: string }>
}
export const deleteUpload = async (name: string) => {
  const r = await fetch('/uploads/' + encodeURIComponent(name), { method: 'DELETE' })
  if (r.status === 401 || r.redirected) { window.location.href = '/login'; throw new Error('auth') }
  return r.json() as Promise<{ ok: boolean }>
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
  body: { message: string; conversation_id: string | null; model: string | null; provider: string | null;
          mode: string; brain_capture?: boolean; brain_context?: boolean },
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
