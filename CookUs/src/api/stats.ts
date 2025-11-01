import api from './axios';

export type ProgressStat = {
  weeklyRate: number;
  cookedCount: number;
  avgDifficulty: number;
  avgMinutes: number;
};

export type LevelRow = { label: '하'|'상'; count: number; ratio?: number };
export type CategoryRow = { label: string; count: number; ratio?: number };

export async function getProgress(signal?: AbortSignal) {
  const { data } = await api.get<ProgressStat>('/me/stats/progress', { signal });
  return data;
}

export async function getLevelDist(signal?: AbortSignal) {
  const { data } = await api.get<Array<{ label: '하'|'상'; count: number }>>(
    '/me/stats/recipe-logs-level',
    { signal }
  );
  const total = Math.max(1, data.reduce((a,b)=>a+(b.count||0),0));
  return (['하','상'] as const).map(lbl => {
    const row = data.find(r=>r.label===lbl) || { label: lbl, count: 0 };
    return { ...row, ratio: row.count / total } as LevelRow;
  });
}

export async function getCategoryDist(signal?: AbortSignal) {
  const { data } = await api.get<Array<{ label: string; count: number }>>(
    '/me/stats/recipe-logs-category',
    { signal }
  );
  const total = Math.max(1, data.reduce((a,b)=>a+(b.count||0),0));
  return [...data].sort((a,b)=>b.count-a.count).slice(0,5)
    .map(r => ({ ...r, ratio: r.count / total })) as CategoryRow[];
}
