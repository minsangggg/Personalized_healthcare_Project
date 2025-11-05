import { useState } from 'react'
import ModalFrame from './ModalFrame'
import { nutritionAPI } from '../api/nutrition'

type Props = {
  onClose: () => void
  onAdded: () => void
}

export default function AddSupplementModal({ onClose, onAdded }: Props) {
  const [name, setName] = useState('')
  const [dosage, setDosage] = useState('')
  const [unit, setUnit] = useState('mg')
  const [takenAt, setTakenAt] = useState(() => new Date().toISOString().slice(0,16))
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const canSubmit = name.trim() && Number(dosage) > 0 && unit.trim() && takenAt

  const submit = async () => {
    if (!canSubmit || submitting) return
    try {
      setSubmitting(true); setError(null)
      await nutritionAPI.addIntake({
        supplement_name: name.trim(),
        dosage: Number(dosage),
        unit: unit.trim(),
        // convert local datetime input (yyyy-MM-ddTHH:mm) to ISO
        taken_at: new Date(takenAt).toISOString(),
      })
      onAdded()
    } catch (e: any) {
      setError(e?.message ?? '등록 실패')
    } finally { setSubmitting(false) }
  }

  return (
    <ModalFrame title="섭취 기록 추가" onClose={onClose}>
      <div className="form-vert">
        <label>
          <div className="label">영양제명</div>
          <input value={name} onChange={e=>setName(e.target.value)} placeholder="예) 비타민 D" />
        </label>
        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:8 }}>
          <label>
            <div className="label">용량</div>
            <input type="number" inputMode="decimal" value={dosage} onChange={e=>setDosage(e.target.value)} placeholder="예) 1000" />
          </label>
          <label>
            <div className="label">단위</div>
            <input value={unit} onChange={e=>setUnit(e.target.value)} placeholder="예) mg" />
          </label>
        </div>
        <label>
          <div className="label">섭취 시각</div>
          <input type="datetime-local" value={takenAt} onChange={e=>setTakenAt(e.target.value)} />
        </label>
        {error && <div className="error" style={{ marginTop:4 }}>{error}</div>}
        <div style={{ display:'flex', justifyContent:'flex-end', gap:8, marginTop:4 }}>
          <button className="btn ghost" onClick={onClose} disabled={submitting}>취소</button>
          <button className="btn" onClick={submit} disabled={!canSubmit || submitting}>{submitting ? '등록 중…' : '등록'}</button>
        </div>
      </div>
    </ModalFrame>
  )
}

