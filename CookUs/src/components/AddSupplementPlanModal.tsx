import { useState } from 'react'
import ModalFrame from './ModalFrame'
import './AddSupplementPlanModal.css'
import { nutritionAPI, type TimeSlot } from '../api/nutrition'

type Props = { onClose: () => void; onAdded: () => void }

const DAYPARTS = ['아침','점심','저녁'] as const
const TIMINGS = ['식후','공복'] as const

export default function AddSupplementPlanModal({ onClose, onAdded }: Props) {
  const [name, setName] = useState('')
  const [part, setPart] = useState<typeof DAYPARTS[number]>('아침')
  const [timing, setTiming] = useState<typeof TIMINGS[number]>('식후')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const canSubmit = name.trim().length > 0 && !!part && !!timing

  const submit = async () => {
    if (!canSubmit || submitting) return
    try {
      setSubmitting(true); setError(null)
      const slot: TimeSlot = `${part}-${timing}`
      await nutritionAPI.createPlan(name.trim(), slot)
      onAdded()
    } catch (e: any) {
      setError(e?.message ?? '등록 실패')
    } finally { setSubmitting(false) }
  }

  return (
    <ModalFrame title="영양제 등록" onClose={onClose}>
      <div className="form-vert">
        <label>
          <div className="label">영양제 이름</div>
          <input value={name} onChange={e=>setName(e.target.value)} placeholder="예) 비타민 D" />
        </label>
        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:8 }}>
          <label>
            <div className="label">시간대</div>
            <select value={part} onChange={(e)=>setPart(e.target.value as any)}>
              {DAYPARTS.map(p => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
          </label>
          <label>
            <div className="label">섭취 조건</div>
            <select value={timing} onChange={(e)=>setTiming(e.target.value as any)}>
              {TIMINGS.map(t => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </label>
        </div>
        {error && <div className="error" style={{ marginTop:4 }}>{error}</div>}
        <div style={{ display:'flex', justifyContent:'flex-end', gap:8 }}>
          <button className="btn ghost" onClick={onClose} disabled={submitting}>취소</button>
          <button className="btn" onClick={submit} disabled={!canSubmit || submitting}>{submitting ? '등록 중…' : '등록'}</button>
        </div>
      </div>
    </ModalFrame>
  )
}
