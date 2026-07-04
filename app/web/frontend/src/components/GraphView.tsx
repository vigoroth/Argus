import { useEffect, useRef, useState } from 'react'
import ForceGraph3D from '3d-force-graph'
import { getGraph } from '../api'

type NodeT = { id: string; label?: string; community?: number; source_file?: string
               file_type?: string; x: number; y: number; z: number }

export default function GraphView() {
  const mountRef = useRef<HTMLDivElement>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const graphRef = useRef<any>(null)
  const [info, setInfo] = useState<NodeT | null>(null)
  const [empty, setEmpty] = useState(false)

  useEffect(() => {
    let disposed = false
    ;(async () => {
      // node-capping for huge graphs happens server-side (get_graph_data) —
      // one place, and less data over the wire
      const data = await getGraph() as { nodes: NodeT[]; links: { source: string; target: string }[] }
      if (disposed || !mountRef.current) return
      if (!data.nodes.length) { setEmpty(true); return }

      const g = new ForceGraph3D(mountRef.current)
        .backgroundColor('rgba(0,0,0,0)')
        .graphData(data)
        .nodeLabel((n: object) => { const t = n as NodeT; return t.label || t.id })
        .nodeAutoColorBy('community')
        .nodeRelSize(4)
        .nodeOpacity(0.95)
        .linkColor(() => 'rgba(214,218,224,0.18)')
        .linkWidth(0.5)
        .linkDirectionalParticles(1)
        .linkDirectionalParticleWidth(1.4)
        .linkDirectionalParticleColor(() => '#9b8cff')
        .onNodeClick((node: object) => {
          const n = node as NodeT
          setInfo(n)
          const dist = 90, r = Math.hypot(n.x, n.y, n.z) || 1
          g.cameraPosition({ x: n.x * (1 + dist / r), y: n.y * (1 + dist / r), z: n.z * (1 + dist / r) }, n, 800)
        })
      graphRef.current = g
      const resize = () => {
        if (mountRef.current) g.width(mountRef.current.clientWidth).height(mountRef.current.clientHeight)
      }
      resize()
      window.addEventListener('resize', resize)
    })()
    return () => {
      disposed = true
      graphRef.current?._destructor?.()
    }
  }, [])

  return (
    <div style={{ flex: 1, position: 'relative', minHeight: 0 }}>
      <div ref={mountRef} style={{ position: 'absolute', inset: 0 }}/>
      {empty && (
        <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center',
                      justifyContent: 'center', color: 'var(--muted)', fontSize: 14 }}>
          No knowledge graph yet — have a few conversations to build it.
        </div>
      )}
      {info && (
        <div style={{ position: 'absolute', top: 16, left: 16, maxWidth: 300, zIndex: 5,
                      background: 'var(--rail)', border: '1px solid var(--hair-2)',
                      borderRadius: 12, padding: '14px 16px' }}>
          <h3 style={{ margin: '0 0 6px', fontSize: 14.5, color: 'var(--violet)' }}>{info.label || info.id}</h3>
          <div style={{ fontSize: 12, color: 'var(--muted)', lineHeight: 1.5, wordBreak: 'break-word' }}>
            {info.source_file && <>source: {info.source_file}<br/></>}
            {info.file_type && <>type: {info.file_type}<br/></>}
            {info.community != null && <>community: {info.community}</>}
          </div>
        </div>
      )}
      <div style={{ position: 'absolute', bottom: 16, right: 16, zIndex: 5, fontSize: 11.5,
                    color: 'var(--muted)', background: 'var(--rail)',
                    border: '1px solid var(--hair-1)', borderRadius: 10, padding: '8px 12px' }}>
        drag to rotate · scroll to zoom · click a node
      </div>
    </div>
  )
}
