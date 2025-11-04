import api from './axios'

export type ProgressStat = {
  weeklyRate: number
  cookedCount: number
  avgDifficulty: number | null
  avgMinutes: number | null
}

export type LevelRow = { label: '상' | '중' | '하'; count: number; ratio?: number }
export type CategoryRow = { label: string; count: number; ratio?: number }

export type ProgressTrendWeek = { week: string; rate: number; cooked: number; goal: number }
export type ProgressTrend = { monthRate: number; weeks: ProgressTrendWeek[] }

// '중'은 백엔드에서 제외됨. 하/상만 제공.
export type LevelWeekly = Array<{ week: string; 상: number; 하: number; total: number }>

export async function getProgress(signal?: AbortSignal, selected?: string) {
  const { data } = await api.get<ProgressStat>('/me/stats/progress', {
    signal,
    params: selected ? { selected_date: selected } : undefined,
  })
  return data
}

export async function getProgressTrend(signal?: AbortSignal, selected?: string) {
  const { data } = await api.get<ProgressTrend>('/me/stats/progress-trend', {
    signal,
    params: selected ? { selected_date: selected } : undefined,
  })
  return data
}

export async function getLevelWeekly(signal?: AbortSignal, selected?: string) {
  const { data } = await api.get<LevelWeekly>('/me/stats/recipe-logs-level-weekly', {
    signal,
    params: selected ? { selected_date: selected } : undefined,
  })
  return data
}

export async function getLevelDist(signal?: AbortSignal, selected?: string) {
  const { data } = await api.get<Array<{ label: LevelRow['label']; count: number; ratio?: number }>>(
    '/me/stats/recipe-logs-level',
    {
      signal,
      params: selected ? { selected_date: selected } : undefined,
    }
  )
  const total = Math.max(1, data.reduce((a,b)=>a+(b.count||0),0))
  return ([ '상','중','하' ] as const).map(lbl => {
    const row = data.find(r=>r.label===lbl) || { label: lbl, count: 0 } as any
    return { ...row, ratio: (row.count || 0) / total } as LevelRow
  })
}

export async function getCategoryMonthly(signal?: AbortSignal, selected?: string) {
  const { data } = await api.get<Array<{ label: string; count: number; ratio?: number }>>(
    '/me/stats/recipe-logs-category',
    {
      signal,
      params: selected ? { selected_date: selected } : undefined,
    }
  )
  const total = Math.max(1, data.reduce((a,b)=>a+(b.count||0),0))
  return [...data].sort((a,b)=>b.count-a.count).slice(0,5)
    .map(r => ({ ...r, ratio: (r.count || 0) / total })) as CategoryRow[]
}
