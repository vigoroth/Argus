import { useEffect, useMemo, useState } from 'react'
import { getCalendar, createEvent, deleteEvent, type CalEvent } from '../api'
import { ChevronLeft, ChevronRight } from './Icons'

const WD = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
  'August', 'September', 'October', 'November', 'December']
const pad = (n: number) => String(n).padStart(2, '0')
const dayKey = (y: number, m: number, d: number) => `${y}-${pad(m + 1)}-${pad(d)}`

export default function CalendarView() {
  const today = new Date()
  const [y, setY] = useState(today.getFullYear())
  const [m, setM] = useState(today.getMonth())
  const [events, setEvents] = useState<CalEvent[]>([])
  const [addDay, setAddDay] = useState<string | null>(null)   // 'YYYY-MM-DD'
  const [form, setForm] = useState({ title: '', time: '12:00' })

  const load = () => getCalendar().then(setEvents).catch(console.error)
  useEffect(() => { load() }, [])

  // group events by their date (YYYY-MM-DD)
  const byDay = useMemo(() => {
    const map: Record<string, CalEvent[]> = {}
    for (const e of events) (map[e.start_ts.slice(0, 10)] ||= []).push(e)
    return map
  }, [events])

  const firstDow = new Date(y, m, 1).getDay()
  const daysIn = new Date(y, m + 1, 0).getDate()
  const cells: (number | null)[] = [
    ...Array(firstDow).fill(null),
    ...Array.from({ length: daysIn }, (_, i) => i + 1),
  ]
  while (cells.length % 7) cells.push(null)

  const step = (delta: number) => {
    const d = new Date(y, m + delta, 1)
    setY(d.getFullYear()); setM(d.getMonth())
  }
  const goToday = () => { setY(today.getFullYear()); setM(today.getMonth()) }

  const submitAdd = async () => {
    if (!addDay || !form.title.trim()) return
    await createEvent({ title: form.title.trim(), start: `${addDay}T${form.time}` })
    setAddDay(null); setForm({ title: '', time: '12:00' })
    load()
  }
  const remove = async (e: CalEvent) => {
    if (!window.confirm(`Delete "${e.title}"?`)) return
    await deleteEvent(e.id); load()
  }

  const todayKey = dayKey(today.getFullYear(), today.getMonth(), today.getDate())
  const btn: React.CSSProperties = { background: 'var(--btn-bg)', border: '1px solid var(--hair-2)',
    borderRadius: 8, color: 'var(--text-2)', cursor: 'pointer', padding: '6px 10px', fontSize: 13 }

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: '20px 28px', minHeight: 0 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 18 }}>
        <h2 style={{ margin: 0, fontSize: 20, color: 'var(--text)' }}>{MONTHS[m]} {y}</h2>
        <div style={{ flex: 1 }}/>
        <button style={btn} onClick={goToday}>Today</button>
        <button style={btn} onClick={() => step(-1)}><ChevronLeft size={15}/></button>
        <button style={btn} onClick={() => step(1)}><ChevronRight size={15}/></button>
        <a href="/calendar.ics" style={{ ...btn, textDecoration: 'none' }}
           title="Subscribe from a calendar app">.ics</a>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7,1fr)', gap: 1,
                    background: 'var(--hair-1)', border: '1px solid var(--hair-1)', borderRadius: 10,
                    overflow: 'hidden' }}>
        {WD.map(d => (
          <div key={d} style={{ background: 'var(--rail)', padding: '8px 10px', fontSize: 12,
                                color: 'var(--faint)', textAlign: 'center' }}>{d}</div>
        ))}
        {cells.map((d, i) => {
          const key = d ? dayKey(y, m, d) : ''
          const evs = d ? (byDay[key] || []) : []
          const isToday = key === todayKey
          return (
            <div key={i} onClick={() => d && setAddDay(key)}
                 style={{ background: 'var(--shell)', minHeight: 96, padding: 6,
                          cursor: d ? 'pointer' : 'default', position: 'relative' }}>
              {d && (
                <div style={{ fontSize: 12, marginBottom: 4,
                              color: isToday ? 'var(--violet)' : 'var(--muted)',
                              fontWeight: isToday ? 700 : 400 }}>{d}</div>
              )}
              {evs.map(e => (
                <div key={e.id} onClick={ev => { ev.stopPropagation(); remove(e) }}
                     title={`${e.start_ts.slice(11, 16)} ${e.title} — click to delete`}
                     style={{ background: 'var(--pill-on)', border: '1px solid var(--pill-br)',
                              borderRadius: 5, padding: '2px 5px', marginBottom: 3, fontSize: 11,
                              color: 'var(--text-2)', whiteSpace: 'nowrap', overflow: 'hidden',
                              textOverflow: 'ellipsis' }}>
                  {e.start_ts.slice(11, 16)} {e.title}
                </div>
              ))}
            </div>
          )
        })}
      </div>
      <div style={{ color: 'var(--faint)', fontSize: 12, marginTop: 10 }}>
        Click a day to add an event · click an event to delete · or just ask Argus in chat.
      </div>

      {addDay && (
        <div onClick={() => setAddDay(null)}
             style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.5)', display: 'flex',
                      alignItems: 'center', justifyContent: 'center', zIndex: 50 }}>
          <div onClick={e => e.stopPropagation()}
               style={{ background: 'var(--rail)', border: '1px solid var(--hair-2)', borderRadius: 12,
                        padding: 22, width: 320 }}>
            <div style={{ color: 'var(--text-2)', fontSize: 14, marginBottom: 12 }}>New event · {addDay}</div>
            <input autoFocus placeholder="Title" value={form.title}
                   onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
                   onKeyDown={e => { if (e.key === 'Enter') submitAdd() }}
                   style={{ width: '100%', padding: '9px 11px', marginBottom: 10, background: 'var(--composer)',
                            border: '1px solid var(--hair-2)', borderRadius: 8, color: 'var(--text)',
                            fontSize: 14, outline: 'none' }}/>
            <input type="time" value={form.time}
                   onChange={e => setForm(f => ({ ...f, time: e.target.value }))}
                   style={{ width: '100%', padding: '9px 11px', marginBottom: 14, background: 'var(--composer)',
                            border: '1px solid var(--hair-2)', borderRadius: 8, color: 'var(--text)',
                            fontSize: 14, outline: 'none' }}/>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
              <button style={btn} onClick={() => setAddDay(null)}>Cancel</button>
              <button onClick={submitAdd}
                      style={{ ...btn, background: 'linear-gradient(180deg,var(--send-a),var(--send-b))',
                               color: '#f1eeff', border: 'none', fontWeight: 600 }}>Add</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
