import { useMemo, useState } from 'react'
import { BadgeIcon, LABELS_KO } from './BadgeSet'
import BadgeDetailModal from './BadgeDetailModal'
import type { BadgeCatalogItem } from '../../data/badges'
import type { BadgeOverview, LockedBadge } from '../../api/badges'

type Props = {
  catalog: BadgeCatalogItem[]
  overview?: BadgeOverview | null
}

export default function BadgeGallery({ catalog, overview }: Props) {
  const [active, setActive] = useState<{ code: string; awardedAt?: string | null; description?: string; title?: string } | null>(null)

  const codeByName = useMemo(() => {
    const map = new Map<string, BadgeCatalogItem>()
    catalog.forEach(item => map.set(item.name_ko.trim(), item))
    return map
  }, [catalog])

  const resolveCatalog = (name: string) => {
    const direct = codeByName.get(name?.trim() ?? '')
    if (direct) return direct
    const normName = normalize(name)
    return catalog.find(item => normalize(item.name_ko) === normName)
  }

  const ownedSet = useMemo(() => {
    const set = new Set<string>()
    overview?.earned?.forEach(badge => {
      const catalogItem = resolveCatalog(badge.name)
      const code = catalogItem?.code ?? slugify(badge.name)
      set.add(code)
    })
    return set
  }, [overview, catalog])

  const ownedMap = useMemo(() => {
    const map = new Map<string, string>()
    overview?.earned?.forEach(badge => {
      const catalogItem = resolveCatalog(badge.name)
      const code = catalogItem?.code ?? slugify(badge.name)
      map.set(code, badge.earned_at)
    })
    return map
  }, [overview, catalog])

  const progressMap = useMemo(() => {
    const map = new Map<string, LockedBadge['progress']>()
    overview?.locked?.forEach(lock => {
      if (!lock.progress) return
      const catalogItem = resolveCatalog(lock.name)
      const code = catalogItem?.code ?? slugify(lock.name)
      map.set(code, lock.progress)
    })
    return map
  }, [overview, catalog])

  const byCategory = useMemo(() => {
    const map: Record<string, BadgeCatalogItem[]> = {}
    catalog.forEach(item => {
      ;(map[item.category] ??= []).push(item)
    })
    return map
  }, [catalog])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {Object.entries(byCategory).map(([cat, items]) => (
        <section key={cat}>
          <h4 style={{ margin: '6px 0 10px', color: '#7a513a' }}>{cat}</h4>
          <div className="badge-grid">
            {items.map(item => {
              const earned = ownedSet.has(item.code)
              const p = progressMap.get(item.code)
              const remaining =
                p && p.target > 0
                  ? Math.max(0, p.remaining ?? p.target - p.current)
                  : item.target_value
                    ? Math.max(0, item.target_value - (p?.current ?? 0))
                    : undefined
              const title = earned
                ? (LABELS_KO as any)[item.code]?.label || item.name_ko
                : remaining != null && item.target_value
                  ? `${item.name_ko} · 남은 목표 ${item.target_value - (p?.current ?? 0)}/${item.target_value}`
                  : item.name_ko

              return (
                <button
                  key={item.code}
                  className={['badge-tile-btn', earned ? 'earned' : 'locked'].join(' ')}
                  title={title}
                  onClick={() =>
                    setActive({
                      code: item.code,
                      awardedAt: ownedMap.get(item.code),
                      description: item.description,
                      title: item.name_ko,
                    })
                  }
                >
                  <div className={earned ? 'shine-wrap flip-y' : ''}>
                    <BadgeIcon code={item.code} earned={earned} size={52} />
                  </div>
                  <div className="badge-name" style={{ marginTop: 4 }}>{item.name_ko}</div>
                </button>
              )
            })}
          </div>
        </section>
      ))}

      {active && (
        <BadgeDetailModal
          code={active.code}
          awardedAt={active.awardedAt}
          description={active.description}
          title={active.title}
          onClose={() => setActive(null)}
        />
      )}
    </div>
  )
}

function normalize(name?: string) {
  return (name ?? '').replace(/\s+/g, '').toLowerCase()
}

function slugify(name?: string) {
  return (name ?? '').trim().toLowerCase().replace(/\s+/g, '_')
}

