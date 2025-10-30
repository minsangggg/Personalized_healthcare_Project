import { useEffect, useRef, useState } from 'react';
import './DashboardTab.css';
import {
  getProgress, getLevelDist, getCategoryDist,
  type ProgressStat, type LevelRow, type CategoryRow
} from '../api/stats';

type Props = {
  isLoggedIn: boolean;
  onRequireLogin: () => void;
  userName?: string;
};

export default function DashboardTab({ isLoggedIn, onRequireLogin, userName }: Props) {
  if (!isLoggedIn) {
    return (
      <section className="app-tab dashboard">
        <div className="card db-card center">
          <h2 className="title">대시보드</h2>
          <p className="sub">로그인이 필요합니다.</p>
          <button className="btn primary" onClick={onRequireLogin}>로그인</button>
        </div>
      </section>
    );
  }
  return <DashboardInner userName={userName} onRequireLogin={onRequireLogin} />;
}

function DashboardInner({ userName, onRequireLogin }: { userName?: string; onRequireLogin: () => void }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string|null>(null);

  const [progress, setProgress] = useState<ProgressStat | null>(null);
  const [levels, setLevels] = useState<LevelRow[]>([]);
  const [categories, setCategories] = useState<CategoryRow[]>([]);

  const abortRef = useRef<AbortController | null>(null);

  const load = async () => {
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;

    setLoading(true); setError(null);
    try {
      const [p, l, c] = await Promise.all([
        getProgress(ac.signal),
        getLevelDist(ac.signal),
        getCategoryDist(ac.signal),
      ]);

      if (ac.signal.aborted) return;
      setProgress(p);
      setLevels(l);
      setCategories(c);
    } catch (e: any) {
      if (ac.signal.aborted) return;
      const status = e?.response?.status;
      const msg = e?.response?.data?.detail || e?.message || '대시보드를 불러오지 못했습니다.';
      setError(msg);
      if (status === 401) onRequireLogin();
    } finally {
      if (!ac.signal.aborted) setLoading(false);
    }
  };

  useEffect(() => {
    load();
    return () => abortRef.current?.abort();
  }, []);

  const badges = makeBadges(progress, levels);

  return (
    <section className="app-tab dashboard">
      <div className="db-header">
        <h2 className="title">{userName ? `${userName}님 대시보드` : '대시보드'}</h2>
        <div className="db-actions">
          <button className="btn ghost" onClick={load} disabled={loading}>새로고침</button>
        </div>
      </div>

      {error && (
        <div className="error" role="alert">
          {error}
          <div style={{ marginTop: 8 }}>
            <button className="btn ghost" onClick={load} disabled={loading}>다시 시도</button>
            <button className="btn ghost" onClick={onRequireLogin} style={{ marginLeft: 6 }}>로그인하기</button>
          </div>
        </div>
      )}

      {badges.length > 0 && (
        <div className="badge-list" aria-live="polite">
          {badges.map((b,i)=>(
            <span key={i} className={`badge ${b.variant ?? ''}`} title={b.hint}>{b.label}</span>
          ))}
        </div>
      )}

      <div className="kpi-grid">
        <Card loading={loading}>
          <Label>이번주 목표 달성률</Label>
          <Big>{progress ? `${progress.weeklyRate}%` : '—'}</Big>
        </Card>
        <Card loading={loading}>
          <Label>이번주 요리 횟수</Label>
          <Big>{progress ? progress.cookedCount : '—'}</Big>
        </Card>
        <Card loading={loading}>
          <Label>평균 난이도</Label>
          <Big>{progress ? diffToText(progress.avgDifficulty) : '—'}</Big>
        </Card>
        <Card loading={loading}>
          <Label>평균 조리시간</Label>
          <Big>{progress ? `${progress.avgMinutes}분` : '—'}</Big>
        </Card>
      </div>

      <section className="db-section">
        <SectionTitle>난이도 분포</SectionTitle>
        {loading ? <SkeletonList rows={3}/> : (
          levels.length === 0 ? <Empty>데이터가 아직 없어요.</Empty> : (
            <ul className="bar-list">
              {levels.map(r => (
                <li key={r.label} className="bar-item">
                  <span className="bar-label">난이도 {r.label}</span>
                  <div className="bar-track">
                    <div className="bar-fill" style={{ width: `${Math.round((r.ratio ?? 0)*100)}%` }} />
                  </div>
                  <span className="bar-val">{r.count}회</span>
                </li>
              ))}
            </ul>
          )
        )}
      </section>

      <section className="db-section">
        <SectionTitle>카테고리 TOP5</SectionTitle>
        {loading ? <SkeletonList rows={5}/> : (
          categories.length === 0 ? <Empty>데이터가 아직 없어요.</Empty> : (
            <ul className="bar-list">
              {categories.map(r => (
                <li key={r.label} className="bar-item">
                  <span className="bar-label">{r.label}</span>
                  <div className="bar-track">
                    <div className="bar-fill" style={{ width: `${Math.round((r.ratio ?? 0)*100)}%` }} />
                  </div>
                  <span className="bar-val">{r.count}회</span>
                </li>
              ))}
            </ul>
          )
        )}
      </section>
    </section>
  );
}

/* ======= 작은 UI 컴포넌트 ======= */
function Card({ children, loading }: { children: React.ReactNode; loading?: boolean }) {
  return (
    <div className="card kpi-card">
      {loading ? <SkeletonBlock height={58}/> : children}
    </div>
  );
}
const Label = ({ children }: { children: React.ReactNode }) => <div className="kpi-label">{children}</div>;
const Big   = ({ children }: { children: React.ReactNode }) => <div className="kpi-big">{children}</div>;
const SectionTitle = ({ children }: { children: React.ReactNode }) => <h3 className="sec-title">{children}</h3>;
const Empty = ({ children }: { children: React.ReactNode }) => <div className="empty">{children}</div>;

function SkeletonBlock({ height=44 }: { height?: number }) {
  return <div className="skeleton" style={{ height }} />;
}
function SkeletonList({ rows=3 }: { rows?: number }) {
  return (
    <div>
      {Array.from({length: rows}).map((_,i)=>(
        <div key={i} style={{marginBottom:8}}>
          <SkeletonBlock height={44}/>
        </div>
      ))}
    </div>
  );
}

/* ======= 헬퍼 ======= */
function diffToText(d?: number | '상' |'하') {
  if (d === '상' ||  d === '하') return d;
  if (d == null) return '—';
  if (d < 1.5) return '하';
  return '상';
}

function makeBadges(p: ProgressStat | null, levels: LevelRow[]) {
  const out: Array<{ label: string; hint?: string; variant?: 'gold'|'mint'|'beige' }> = [];
  if (!p) return out;
  if (p.weeklyRate >= 100) out.push({ label: '🏆 주간 목표 달성', hint: '이번 주 목표를 모두 달성했어요!', variant: 'gold' });
  if (p.cookedCount >= 5) out.push({ label: '🔥 주 5회 달성', hint: '꾸준한 요리 루틴 멋져요!', variant: 'mint' });
  if ((levels.find(l => l.label === '하')?.ratio ?? 0) >= 0.6) out.push({ label: '🌱 쉬운 요리 마스터', hint: '쉬운 레시피로 루틴을 잘 유지 중', variant: 'beige' });
  return out;
}
