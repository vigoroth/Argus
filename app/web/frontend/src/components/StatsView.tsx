import { useEffect, useRef, useState } from 'react'
import type { Stats } from '../api'
import { getStats } from '../api'

const fmtMs = (ms: number) => ms >= 1000 ? (ms / 1000).toFixed(1) + 's' : Math.round(ms) + 'ms'
const fmtCost = (c: number) => '$' + (c < 0.01 ? c.toFixed(4) : c.toFixed(2))
const fmtNum = (n: number) => n >= 1e6 ? (n / 1e6).toFixed(1) + 'M' : n >= 1e3 ? (n / 1e3).toFixed(1) + 'k' : String(n)

function Tile({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div style={{ background: 'var(--rail)', border: '1px solid var(--hair-1)',
                  borderRadius: 12, padding: '12px 14px' }}>
      <div style={{ fontSize: 10.5, letterSpacing: 1, textTransform: 'uppercase', color: 'var(--faint)' }}>{k}</div>
      <div style={{ fontSize: 22, fontWeight: 640, marginTop: 3 }}>{v}</div>
    </div>
  )
}

// single-series bars: thin marks, rounded top on the baseline, hairline grid,
// direct label on the max only, per-bar hover tooltip (dataviz spec)
function BarChart({ pts, color, fmt }: {
  pts: { x: string; y: number }[]; color: string; fmt: (v: number) => string
}) {
  const [tip, setTip] = useState<{ x: number; y: number; text: string } | null>(null)
  const W = 320, H = 120, padB = 16, padT = 12
  if (!pts.length) return <div style={{ height: H, color: 'var(--faint)', fontSize: 12 }}>no data</div>
  const max = Math.max(...pts.map(p => p.y)) || 1
  const iMax = pts.findIndex(p => p.y === max)
  const slot = W / pts.length
  const bw = Math.max(3, Math.min(26, slot - 2))
  return (
    <div style={{ position: 'relative' }}>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ display: 'block', width: '100%', height: H }}>
        {[0.5, 1].map(f => (
          <line key={f} x1={0} x2={W} y1={padT + (H - padT - padB) * (1 - f)} y2={padT + (H - padT - padB) * (1 - f)}
                stroke="rgba(255,255,255,0.07)" strokeWidth={1}/>
        ))}
        {pts.map((p, i) => {
          const h = Math.max(1, (H - padT - padB) * (p.y / max))
          const x = i * slot + (slot - bw) / 2, y = H - padB - h
          const r = Math.min(4, bw / 2, h)
          return (
            <g key={i}>
              <path fill={color}
                    d={`M${x} ${H - padB} v${-(h - r)} q0 ${-r} ${r} ${-r} h${bw - 2 * r} q${r} 0 ${r} ${r} v${h - r} z`}
                    onMouseMove={e => setTip({ x: e.clientX, y: e.clientY, text: `${p.x} · ${fmt(p.y)}` })}
                    onMouseLeave={() => setTip(null)}/>
              {i === iMax && <text x={x + bw / 2} y={y - 4} textAnchor="middle" fill="#c8ccd2" fontSize={10}>{fmt(p.y)}</text>}
            </g>
          )
        })}
        <text x={0} y={H - 3} fill="#7b818a" fontSize={9}>{pts[0].x.slice(5)}</text>
        <text x={W} y={H - 3} textAnchor="end" fill="#7b818a" fontSize={9}>{pts[pts.length - 1].x.slice(5)}</text>
        <line x1={0} x2={W} y1={H - padB} y2={H - padB} stroke="rgba(255,255,255,0.14)" strokeWidth={1}/>
      </svg>
      {tip && (
        <div style={{ position: 'fixed', left: tip.x + 12, top: tip.y - 10, zIndex: 50,
                      pointerEvents: 'none', background: 'var(--rail)',
                      border: '1px solid var(--hair-2)', borderRadius: 8, padding: '6px 9px',
                      fontSize: 12, fontVariantNumeric: 'tabular-nums' }}>{tip.text}</div>
      )}
    </div>
  )
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ background: 'var(--rail)', border: '1px solid var(--hair-1)',
                  borderRadius: 12, padding: '12px 14px 8px' }}>
      <h4 style={{ margin: '0 0 8px', fontSize: 12.5, fontWeight: 550, color: 'var(--muted)' }}>{title}</h4>
      {children}
    </div>
  )
}

export default function StatsView() {
  const [stats, setStats] = useState<Stats | null>(null)
  const timerRef = useRef<number>(0)

  useEffect(() => {
    const load = () => { if (document.visibilityState === 'visible') getStats().then(setStats).catch(console.error) }
    load()
    timerRef.current = window.setInterval(load, 15000)
    return () => window.clearInterval(timerRef.current)
  }, [])

  if (!stats) return <div style={{ padding: 40, color: 'var(--muted)' }}>loading ...</div>
  const t = stats.totals
  const td: React.CSSProperties = { padding: '4px 8px', borderBottom: '1px solid var(--hair-1)',
                                    fontVariantNumeric: 'tabular-nums' }
  const num: React.CSSProperties = { ...td, textAlign: 'right' }

  return (
    <div style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>
      <div style={{ maxWidth: 1060, margin: '0 auto', padding: '20px 22px 30px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(150px,1fr))', gap: 10 }}>
          <Tile k="Runs" v={fmtNum(t.runs)}/>
          <Tile k="Success" v={t.runs ? Math.round(t.success_rate * 100) + '%' : '—'}/>
          <Tile k="Avg latency" v={t.runs ? fmtMs(t.avg_ms) : '—'}/>
          <Tile k="p95 latency" v={t.runs ? fmtMs(t.p95_ms) : '—'}/>
          <Tile k="Tokens" v={fmtNum(t.input_tokens + t.output_tokens)}/>
          <Tile k="Total cost" v={fmtCost(t.cost_usd)}/>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(300px,1fr))',
                      gap: 10, marginTop: 10 }}>
          <Card title="Runs per day">
            <BarChart pts={stats.daily.map(p => ({ x: p.day, y: p.runs }))} color="var(--s-runs)" fmt={fmtNum}/>
          </Card>
          <Card title="Cost per day (USD)">
            <BarChart pts={stats.daily.map(p => ({ x: p.day, y: p.cost }))} color="var(--s-cost)" fmt={fmtCost}/>
          </Card>
          <Card title="Avg latency per day (s)">
            <BarChart pts={stats.daily.map(p => ({ x: p.day, y: p.avg_ms / 1000 }))} color="var(--s-lat)"
                      fmt={v => v.toFixed(1) + 's'}/>
          </Card>
        </div>
        <div style={{ background: 'var(--rail)', border: '1px solid var(--hair-1)',
                      borderRadius: 12, padding: '12px 14px', marginTop: 10 }}>
          <h4 style={{ margin: '0 0 8px', fontSize: 12.5, fontWeight: 550, color: 'var(--muted)' }}>Recent runs</h4>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12.5 }}>
            <thead>
              <tr>{['time', 'model', 'latency', 'tokens', 'cost', ''].map((h, i) => (
                <th key={i} style={{ textAlign: i >= 2 && i <= 4 ? 'right' : 'left', color: 'var(--faint)',
                                     fontWeight: 500, padding: '4px 8px',
                                     borderBottom: '1px solid var(--hair-1)' }}>{h}</th>))}
              </tr>
            </thead>
            <tbody>
              {stats.recent.map((r, i) => (
                <tr key={i} style={{ color: r.ok ? undefined : 'var(--crit)' }}>
                  <td style={td}>{r.ts}</td>
                  <td style={td}>{r.model}</td>
                  <td style={num}>{fmtMs(r.ms)}</td>
                  <td style={num}>{fmtNum(r.tokens)}</td>
                  <td style={num}>{fmtCost(r.cost)}</td>
                  <td style={td}>{r.ok
                    ? <span style={{ color: 'var(--ok)' }}>✓ ok</span>
                    : <span style={{ color: 'var(--crit)' }}>✕ fail</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {t.runs === 0 && (
            <div style={{ color: 'var(--muted)', textAlign: 'center', padding: '40px 0' }}>
              No runs recorded yet — send a chat message first.
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
