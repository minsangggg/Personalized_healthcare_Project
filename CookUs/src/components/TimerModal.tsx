import { useEffect, useMemo, useRef, useState } from 'react'
import ModalFrame from './ModalFrame'
import './TimerModal.css'

export default function TimerModal({ onClose, defaultMinutes }: { onClose: () => void; defaultMinutes?: number }) {
  const [hh, setHh] = useState<string>(() => format2(Math.floor((defaultMinutes ?? 0) / 60)))
  const [mm, setMm] = useState<string>(() => format2((defaultMinutes ?? 0) % 60))
  const [ss, setSs] = useState<string>('00')

  const [remaining, setRemaining] = useState<number>(0)
  const [running, setRunning] = useState(false)
  const [done, setDone] = useState(false)
  const tickRef = useRef<number | null>(null)

  const total = useMemo(() => toSeconds(hh, mm, ss), [hh, mm, ss])

  useEffect(() => {
    if (!running) return
    if (remaining <= 0) { setRunning(false); setDone(true); return }
    tickRef.current = window.setInterval(() => {
      setRemaining((r) => {
        if (r <= 1) {
          window.clearInterval(tickRef.current || undefined)
          tickRef.current = null
          setRunning(false)
          setDone(true)
          return 0
        }
        return r - 1
      })
    }, 1000)
    return () => { if (tickRef.current) { window.clearInterval(tickRef.current); tickRef.current = null } }
  }, [running, remaining])

  const start = () => {
    const t = total
    if (t <= 0) return
    if (remaining <= 0 || done) setRemaining(t)
    setDone(false)
    setRunning(true)
  }
  const pause = () => setRunning(false)
  const reset = () => { setRunning(false); setDone(false); setRemaining(0) }

  const disp = formatHMS(remaining > 0 ? remaining : total)

  return (
    <ModalFrame title="요리 타이머" onClose={onClose}>
      <div className="timer-wrap">
        <div className="timer-inputs">
          <TimeInput label="시" value={hh} onChange={setHh} max={99} />
          <span className="colon">:</span>
          <TimeInput label="분" value={mm} onChange={setMm} max={59} />
          <span className="colon">:</span>
          <TimeInput label="초" value={ss} onChange={setSs} max={59} />
        </div>

        <div className={`timer-display ${done ? 'done' : ''}`}>{disp}</div>

        <div className="timer-actions">
          {!running && <button className="btn primary" onClick={start} disabled={total<=0}>시작</button>}
          {running && <button className="btn warn" onClick={pause}>일시정지</button>}
          <button className="btn ghost" onClick={reset}>초기화</button>
        </div>

        {done && <div className="timer-done">타이머 완료!</div>}
      </div>
    </ModalFrame>
  )
}

function TimeInput({ label, value, onChange, max }: { label: string; value: string; onChange: (v: string)=>void; max: number }){
  const norm = (v: string) => {
    const n = Math.max(0, Math.min(max, Number(v.replace(/[^0-9]/g,'') || '0')))
    return format2(n)
  }
  return (
    <label className="tcell">
      <input
        inputMode="numeric"
        pattern="[0-9]*"
        value={value}
        onChange={(e)=>onChange(norm(e.target.value))}
        onBlur={(e)=>onChange(norm(e.target.value))}
      />
      <span className="lbl">{label}</span>
    </label>
  )
}

function toSeconds(hh: string, mm: string, ss: string){
  const h = Number(hh) || 0
  const m = Number(mm) || 0
  const s = Number(ss) || 0
  return h*3600 + m*60 + s
}
function format2(n: number){ return String(Math.max(0, Math.min(99, Math.floor(n)))).padStart(2,'0') }
function formatHMS(total: number){
  total = Math.max(0, Math.floor(total))
  const h = Math.floor(total/3600)
  const m = Math.floor((total%3600)/60)
  const s = total%60
  return `${format2(h)}:${format2(m)}:${format2(s)}`
}

// Inline, non-overlay version for embedding inside another modal/content
export function TimerInlinePanel({ onClose, defaultMinutes }: { onClose: () => void; defaultMinutes?: number }){
  const [hh, setHh] = useState<string>(() => format2(Math.floor((defaultMinutes ?? 0) / 60)))
  const [mm, setMm] = useState<string>(() => format2((defaultMinutes ?? 0) % 60))
  const [ss, setSs] = useState<string>('00')
  const [remaining, setRemaining] = useState<number>(0)
  const [running, setRunning] = useState(false)
  const [done, setDone] = useState(false)
  const tickRef = useRef<number | null>(null)

  const total = useMemo(() => toSeconds(hh, mm, ss), [hh, mm, ss])

  useEffect(() => {
    if (!running) return
    if (remaining <= 0) { setRunning(false); setDone(true); return }
    tickRef.current = window.setInterval(() => {
      setRemaining((r) => {
        if (r <= 1) {
          window.clearInterval(tickRef.current || undefined)
          tickRef.current = null
          setRunning(false)
          setDone(true)
          return 0
        }
        return r - 1
      })
    }, 1000)
    return () => { if (tickRef.current) { window.clearInterval(tickRef.current); tickRef.current = null } }
  }, [running, remaining])

  const start = () => {
    const t = total
    if (t <= 0) return
    if (remaining <= 0 || done) setRemaining(t)
    setDone(false)
    setRunning(true)
  }
  const pause = () => setRunning(false)
  const reset = () => { setRunning(false); setDone(false); setRemaining(0) }
  const disp = formatHMS(remaining > 0 ? remaining : total)

  return (
    <div className="timer-inline" onClick={(e)=>e.stopPropagation()}>
      <div className="ti-head">
        <div className="ti-title">요리 타이머</div>
        <button className="ti-x" onClick={onClose}>×</button>
      </div>
      <div className="timer-wrap">
        <div className="timer-inputs">
          <TimeInput label="시" value={hh} onChange={setHh} max={99} />
          <span className="colon">:</span>
          <TimeInput label="분" value={mm} onChange={setMm} max={59} />
          <span className="colon">:</span>
          <TimeInput label="초" value={ss} onChange={setSs} max={59} />
        </div>
        <div className={`timer-display ${done ? 'done' : ''}`}>{disp}</div>
        <div className="timer-actions">
          {!running && <button className="btn primary" onClick={start} disabled={total<=0}>시작</button>}
          {running && <button className="btn warn" onClick={pause}>일시정지</button>}
          <button className="btn ghost" onClick={reset}>초기화</button>
        </div>
        {done && <div className="timer-done">타이머 완료!</div>}
      </div>
    </div>
  )
}
