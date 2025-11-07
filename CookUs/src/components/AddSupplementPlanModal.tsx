import { useState } from 'react'
import ModalFrame from './ModalFrame'
import './AddSupplementPlanModal.css'
import { nutritionAPI, type TimeSlot } from '../api/nutrition'

type Props = { onClose: () => void; onAdded: () => void; plan?: { plan_id: number; supplement_name: string; time_slot: string } }

const DAYPARTS = ['아침','점심','저녁'] as const
const TIMINGS = ['식후','공복'] as const

export default function AddSupplementPlanModal({ onClose, onAdded, plan }: Props) {
  const initialName = plan?.supplement_name ?? ''
  const initialPart = (plan?.time_slot?.split('-')[0] as typeof DAYPARTS[number]) || '아침'
  const initialTiming = (plan?.time_slot?.split('-')[1] as typeof TIMINGS[number]) || '식후'
  const [name, setName] = useState(initialName)
  const [part, setPart] = useState<typeof DAYPARTS[number]>(initialPart)
  const [timing, setTiming] = useState<typeof TIMINGS[number]>(initialTiming)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const canSubmit = name.trim().length > 0 && !!part && !!timing

  const submit = async () => {
    if (!canSubmit || submitting) return
    try {
      setSubmitting(true); setError(null)
      const slot: TimeSlot = `${part}-${timing}`
      if (plan) {
        await nutritionAPI.updatePlan(plan.plan_id, name.trim(), slot)
      } else {
        await nutritionAPI.createPlan(name.trim(), slot)
      }
      onAdded()
    } catch (e: any) {
      setError(e?.message ?? '등록 실패')
    } finally { setSubmitting(false) }
  }

  return (
    <ModalFrame title={plan ? '영양제 수정' : '영양제 등록'} onClose={onClose}>
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
          <button className="btn" onClick={submit} disabled={!canSubmit || submitting}>{submitting ? (plan ? '수정 중…' : '등록 중…') : (plan ? '수정' : '등록')}</button>
        </div>
      </div>
    </ModalFrame>
  )
}
