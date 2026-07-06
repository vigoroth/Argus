import { useEffect, useRef, useState } from 'react'
import { deleteUpload, getUploads, uploadFile, type UploadInfo } from '../api'

const fmtSize = (b: number) =>
  b < 1024 ? `${b} B` : b < 1048576 ? `${(b / 1024).toFixed(1)} KB` : `${(b / 1048576).toFixed(1)} MB`

// Data tab: drop files for the data-analyst subagent; Analyze hands the path
// to a chat turn that spawns it.
export default function DataView({ onAnalyze }: { onAnalyze: (path: string) => void }) {
  const [files, setFiles] = useState<UploadInfo[]>([])
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const [drag, setDrag] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const refresh = () => getUploads().then(setFiles).catch(console.error)
  useEffect(() => { refresh() }, [])

  const up = async (list: FileList | null) => {
    if (!list?.length || busy) return
    setBusy(true); setErr('')
    try {
      for (const f of Array.from(list)) await uploadFile(f)
      refresh()
    } catch (e) { setErr(String(e)) } finally { setBusy(false) }
  }

  const remove = async (name: string) => {
    if (!window.confirm(`Delete "${name}"?`)) return
    await deleteUpload(name); refresh()
  }

  const btn: React.CSSProperties = { padding: '5px 12px', borderRadius: 8, fontSize: 12.5,
    cursor: 'pointer', border: '1px solid var(--hair-2)', background: 'var(--btn-bg)',
    color: 'var(--text-2)' }

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: '20px 28px', minHeight: 0 }}>
      <h2 style={{ margin: '0 0 4px', fontSize: 20, color: 'var(--text)' }}>Data</h2>
      <div style={{ color: 'var(--faint)', fontSize: 12.5, marginBottom: 16 }}>
        Upload CSV / Excel / JSON / SQLite files, then let the data-analyst subagent
        profile and report on them. 200 MB max per file.
      </div>

      <div onClick={() => inputRef.current?.click()}
           onDragOver={e => { e.preventDefault(); setDrag(true) }}
           onDragLeave={() => setDrag(false)}
           onDrop={e => { e.preventDefault(); setDrag(false); up(e.dataTransfer.files) }}
           style={{ border: `2px dashed ${drag ? 'var(--violet)' : 'var(--hair-2)'}`,
                    borderRadius: 12, padding: '34px 20px', textAlign: 'center',
                    color: drag ? 'var(--violet)' : 'var(--muted)', cursor: 'pointer',
                    marginBottom: 18, background: drag ? 'var(--hover)' : 'transparent' }}>
        {busy ? 'Uploading…' : 'Drop files here or click to browse'}
        <input ref={inputRef} type="file" multiple hidden
               accept=".csv,.tsv,.txt,.json,.xlsx,.xls,.parquet,.sqlite,.db"
               onChange={e => { up(e.target.files); e.target.value = '' }}/>
      </div>
      {err && <div style={{ color: 'var(--grad-a)', fontSize: 12, marginBottom: 12 }}>{err}</div>}

      {files.map(f => (
        <div key={f.name} style={{ display: 'flex', alignItems: 'center', gap: 10,
                                   background: 'var(--rail)', border: '1px solid var(--hair-1)',
                                   borderRadius: 10, padding: '10px 14px', marginBottom: 8 }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 13.5, color: 'var(--text)', overflow: 'hidden',
                          textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{f.name}</div>
            <div style={{ fontSize: 11, color: 'var(--faint)' }}>
              {fmtSize(f.size)} · {new Date(f.mtime * 1000).toLocaleString()}
            </div>
          </div>
          <button style={{ ...btn, color: 'var(--violet)', borderColor: 'var(--pill-br)' }}
                  onClick={() => onAnalyze('data/uploads/' + f.name)}>Analyze</button>
          <button style={{ ...btn, color: '#e66767', borderColor: '#5b3333' }}
                  onClick={() => remove(f.name)}>Delete</button>
        </div>
      ))}
      {files.length === 0 && !busy && (
        <div style={{ color: 'var(--faint)', fontSize: 13 }}>No files uploaded yet.</div>
      )}
    </div>
  )
}
