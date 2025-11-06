import { useMemo, useState } from 'react';
import { BadgeIcon, LABELS_KO } from './BadgeSet';
import BadgeDetailModal from './BadgeDetailModal';
import type { BadgeCatalogItem, UserBadge, BadgeProgress } from '../../mocks/badges';

type Props = {
  catalog: BadgeCatalogItem[];
  owned: UserBadge[];
  progress: BadgeProgress[];
};

export default function BadgeGallery({ catalog, owned, progress }: Props) {
  const [active, setActive] = useState<{ code: string; awardedAt?: string | null; description?: string } | null>(null);

  const ownedSet = useMemo(() => new Set(owned.map(b => b.code)), [owned]);
  const ownedMap = useMemo(() => Object.fromEntries(owned.map(b => [b.code, b.awarded_at])) as Record<string, string>, [owned]);
  const progMap = useMemo(() => Object.fromEntries(progress.map(p => [p.code, p])) as Record<string, BadgeProgress>, [progress]);

  const byCategory = useMemo(() => {
    const map: Record<string, BadgeCatalogItem[]> = {};
    for (const b of catalog) {
      (map[b.category] ??= []).push(b);
    }
    return map;
  }, [catalog]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {Object.entries(byCategory).map(([cat, items]) => (
        <section key={cat}>
          <h4 style={{ margin: '6px 0 10px', color: '#7a513a' }}>{cat}</h4>
          <div className="badge-grid">
            {items.map(item => {
              const earned = ownedSet.has(item.code);
              const p = progMap[item.code];
              const remain = p && !p.is_completed ? Math.max(0, p.target_value - p.current_value) : undefined;
              const title = earned
                ? (LABELS_KO as any)[item.code]?.label || item.name_ko
                : remain != null && item.target_value
                ? `${item.name_ko} · 남은 목표: ${remain}/${item.target_value}`
                : item.name_ko;
              return (
                <button
                  key={item.code}
                  className={['badge-tile-btn', earned ? 'earned' : 'locked'].join(' ')}
                  title={title}
                  onClick={() => setActive({ code: item.code, awardedAt: ownedMap[item.code], description: item.description })}
                >
                  <div className={earned ? 'shine-wrap flip-y' : ''}>
                    <BadgeIcon code={item.code} earned={earned} size={52} />
                  </div>
                  <div className="badge-name" style={{ marginTop: 4 }}>{item.name_ko}</div>
                </button>
              );
            })}
          </div>
        </section>
      ))}

      {active && (
        <BadgeDetailModal
          code={active.code}
          awardedAt={active.awardedAt}
          description={active.description}
          onClose={() => setActive(null)}
        />
      )}
    </div>
  );
}
