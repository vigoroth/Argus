import { useState } from 'react'

// Research plan-approval gate (the "plan mode" checkpoint). Shows the proposed
// sub-questions as an editable list; approving resumes the run with YOUR edits.
export default function PlanApproval({ plan, disabled, onApprove }: {
  plan: string[]; disabled: boolean
  onApprove: (edited: string[]) => void
}) {
  // one sub-question per line — simplest editable representation
  const [text, setText] = useState(plan.join('\n'))

  const approve = () => {
    const edited = text.split('\n').map(s => s.trim()).filter(Boolean)
    if (edited.length) onApprove(edited)
  }

  return (
    <div style={{ maxWidth: 900, margin: '4px auto 0', width: '100%', padding: '0 36px' }}>
      <div style={{ background: 'var(--rail)', border: '1px solid var(--pill-br)',
                    borderRadius: 12, padding: '14px 16px' }}>
        <div style={{ color: 'var(--text-2)', fontSize: 13, marginBottom: 8, fontWeight: 600 }}>
          🔬 Research plan — review &amp; edit the sub-questions, then approve
        </div>
        <textarea value={text} disabled={disabled}
          onChange={e => setText(e.target.value)}
          rows={Math.max(3, text.split('\n').length)}
          style={{ width: '100%', background: 'var(--composer)', color: 'var(--text)',
                   border: '1px solid var(--hair-2)', borderRadius: 8, padding: '10px 12px',
                   fontSize: 13.5, lineHeight: 1.7, resize: 'vertical', outline: 'none',
                   fontFamily: 'inherit' }}/>
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 10 }}>
          <button onClick={approve} disabled={disabled}
            style={{ padding: '8px 18px', border: 'none', borderRadius: 9, fontSize: 13.5,
                     cursor: disabled ? 'default' : 'pointer', opacity: disabled ? .5 : 1,
                     color: '#f1eeff', fontWeight: 600,
                     background: 'linear-gradient(180deg,var(--send-a),var(--send-b))' }}>
            Approve &amp; Research
          </button>
        </div>
      </div>
    </div>
  )
}
