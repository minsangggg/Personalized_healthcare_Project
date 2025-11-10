import { useMemo } from 'react'
import type { DayStatus } from '../api/nutrition'

type Props = {
  month: Date
  onMonthChange: (d: Date) => void
  monthStatus: Map<string, DayStatus>
  onSelectDay: (ymd: string) => void
  selectedDay: string | null
}

export default function NutritionCalendar({ month, onMonthChange, monthStatus, onSelectDay, selectedDay }: Props) {
  const cells = useMemo(() => getCalendarGrid(month), [month])
  const now = new Date()
  const todayStr = ymd(now)
  const monthLabel = `${month.getFullYear()}년 ${month.getMonth() + 1}월`
  const isSameMonth = (d: Date) => d.getFullYear() === month.getFullYear() && d.getMonth() === month.getMonth()

  const goPrev = () => onMonthChange(new Date(month.getFullYear(), month.getMonth() - 1, 1))
  const goNext = () => onMonthChange(new Date(month.getFullYear(), month.getMonth() + 1, 1))
  const goToday = () => {
    const base = new Date(now.getFullYear(), now.getMonth(), 1)
    onMonthChange(base)
    onSelectDay(todayStr)
  }

  return (
    <div className="cal-card">
      <div className="cal-header">
        <h3 className="title" style={{ margin:0 }}>{monthLabel}</h3>
        <div className="cal-controls">
          <button className="btn ghost" onClick={goPrev} aria-label="이전 달">‹</button>
          <button className="btn ghost" onClick={goNext} aria-label="다음 달">›</button>
          <button className="btn" onClick={goToday}>오늘</button>
        </div>
      </div>
      <div className="calendar">
        <div className="week-head">
          {['월','화','수','목','금','토','일'].map((w) => (
            <div key={w} className="cell head">{w}</div>
          ))}
        </div>
        <div className="weeks">
          {cells.map((d, i) => {
            const dayStr = ymd(d)
            const inMonth = isSameMonth(d)
            const stat = monthStatus.get(dayStr)
            const isFuture = new Date(d.getFullYear(), d.getMonth(), d.getDate()) > new Date(now.getFullYear(), now.getMonth(), now.getDate())
            const classes = [
              'cell','day',
              inMonth ? 'cur' : 'dim',
              dayStr === todayStr ? 'today' : '',
              selectedDay === dayStr ? 'sel' : '',
              colorOf(stat) ? 'has' : ''
            ].join(' ').trim()
            return (
              <button
                key={`${d.getTime()}-${i}`}
                className={classes}
                onClick={() => onSelectDay(dayStr)}
                title={titleOf(stat)}
              >
                <span className="dnum">{d.getDate()}</span>
                {/* status indicator color dot */}
                {stat && <span className="dot" aria-hidden style={{ background: dotColor(stat, isFuture) }} />}
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}

function firstDayOfMonth(d: Date) { return new Date(d.getFullYear(), d.getMonth(), 1) }
function lastDayOfMonth(d: Date) { return new Date(d.getFullYear(), d.getMonth() + 1, 0) }

function getCalendarGrid(base: Date) {
  const first = firstDayOfMonth(base)
  const last = lastDayOfMonth(base)
  const firstWeekdayMonStart = ((first.getDay() + 6) % 7)
  const daysInMonth = last.getDate()
  const cells: Date[] = []
  for (let i = 0; i < firstWeekdayMonStart; i++) {
    const d = new Date(first)
    d.setDate(first.getDate() - (firstWeekdayMonStart - i))
    cells.push(d)
  }
  for (let i = 1; i <= daysInMonth; i++) {
    cells.push(new Date(base.getFullYear(), base.getMonth(), i))
  }
  while (cells.length < 42) {
    const d = new Date(cells[cells.length - 1])
    d.setDate(d.getDate() + 1)
    cells.push(d)
  }
  return cells
}

function ymd(d: Date) {
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day}`
}

function colorOf(stat?: DayStatus) {
  if (!stat) return ''
  return 'has'
}

function dotColor(stat: DayStatus, isFuture: boolean) {
  if (isFuture) return '#9ca3af' // gray for future dates

  const taken = Math.max(0, stat.taken ?? 0)
  const total = Math.max(0, stat.total ?? 0)

  if (taken === 0) {
    return total === 0 ? '#9ca3af' : '#ef4444' // nothing scheduled vs missed
  }
  if (total === 0) return '#16a34a' // historical intake that no longer has a plan
  if (taken >= total) return '#16a34a' // completed (protect against stale totals)
  return '#f59e0b' // partial
}

function titleOf(stat?: DayStatus) {
  if (!stat) return undefined
  return `체크: ${stat.taken}/${stat.total}`
}
