import { useMemo, useState } from 'react'
import { BadgeIcon } from './BadgeSet'
import BadgeDetailModal from './BadgeDetailModal'
import type { BadgeOverview } from '../../api/badges'
import { badgeCategoryLabels, badgeMetaById, badgeDisplayOrder, type BadgeCategoryKey } from '../../data/badges'

type Props = {
  overview?: BadgeOverview | null
  displayedBadgeId?: number | null
  onDisplayChange?: (badgeId: number | null) => Promise<boolean>
  displayLoading?: boolean
  displayError?: string | null
}

type EnrichedBadge = {
  id: number
  name: string
  categoryKey: BadgeCategoryKey
  categoryLabel: string
  iconCode?: string
  description?: string
  earnedAt?: string | null
  progress?: { current: number; target: number; remaining: number }
  target?: number
}

const categoryOrder: BadgeCategoryKey[] = ['contest', 'ranks', 'likes', 'recipe', 'cooked', 'fridge', 'goal', 'others']

export default function BadgeGallery({
  overview,
  displayedBadgeId,
  onDisplayChange,
  displayLoading,
  displayError,
}: Props) {
  const [active, setActive] = useState<{ id: number; code?: string; title: string; description?: string; awardedAt?: string | null; categoryLabel?: string; owned: boolean } | null>(null)

  const earnedMap = useMemo(() => {
    const map = new Map<number, BadgeOverview['earned'][number]>()
    overview?.earned?.forEach(item => map.set(item.badge_id, item))
    return map
  }, [overview])

  const lockedMap = useMemo(() => {
    const map = new Map<number, BadgeOverview['locked'][number]>()
    overview?.locked?.forEach(item => map.set(item.badge_id, item))
    return map
  }, [overview])

  const allIds = useMemo(() => {
    const ids = new Set<number>()
    badgeDisplayOrder.forEach(id => ids.add(id))
    earnedMap.forEach((_, id) => ids.add(id))
    lockedMap.forEach((_, id) => ids.add(id))
    return Array.from(ids)
  }, [earnedMap, lockedMap])

  const idOrderIndex = (id: number) => {
    const idx = badgeDisplayOrder.indexOf(id)
    return idx === -1 ? Number.MAX_SAFE_INTEGER : idx
  }

  const grouped = useMemo(() => {
    const map = new Map<BadgeCategoryKey, EnrichedBadge[]>()

    allIds.forEach(id => {
      const meta = badgeMetaById[id]
      const earned = earnedMap.get(id)
      const locked = lockedMap.get(id)
      const categoryKey = meta?.category ?? (earned?.category as BadgeCategoryKey) ?? (locked?.category as BadgeCategoryKey) ?? 'others'
      const categoryLabel = badgeCategoryLabels[categoryKey] ?? badgeCategoryLabels.others
      const name = earned?.name ?? locked?.name ?? meta?.description ?? `배지 #${id}`

      const entry: EnrichedBadge = {
        id,
        name,
        categoryKey,
        categoryLabel,
        iconCode: meta?.iconCode,
        description: meta?.description,
        earnedAt: earned?.earned_at ?? null,
        progress: locked?.progress ? { ...locked.progress } : undefined,
        target: meta?.target ?? locked?.progress?.target,
      }

      if (!map.has(categoryKey)) {
        map.set(categoryKey, [])
      }
      map.get(categoryKey)!.push(entry)
    })

    map.forEach(list => list.sort((a, b) => idOrderIndex(a.id) - idOrderIndex(b.id)))

    return map
  }, [allIds, earnedMap, lockedMap])

  const sections = categoryOrder.filter(key => (grouped.get(key)?.length ?? 0) > 0)

  if (sections.length === 0) {
    return <div className="note">아직 획득하거나 진행 중인 배지가 없어요.</div>
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {sections.map(categoryKey => {
        const items = grouped.get(categoryKey) ?? []
        return (
          <section key={categoryKey}>
            <h4 style={{ margin: '6px 0 10px', color: '#7a513a' }}>{badgeCategoryLabels[categoryKey]}</h4>
            <div className="badge-grid">
              {items.map(item => {
                const owned = Boolean(item.earnedAt)
                const remaining = !owned
                  ? item.progress?.remaining ??
                    (item.progress && item.progress.target != null
                      ? Math.max(item.progress.target - item.progress.current, 0)
                      : item.target ?? undefined)
                  : undefined
                const buttonTitle = owned
                  ? `${item.name} · 획득일 ${new Date(item.earnedAt!).toLocaleDateString()}`
                  : remaining != null
                    ? `${item.name} · 남은 목표 ${remaining}`
                    : item.description ?? item.name

                return (
                  <button
                    key={item.id}
                    className={[
                      'badge-tile-btn',
                      owned ? 'earned' : 'locked',
                      owned && item.id === displayedBadgeId ? 'displayed' : '',
                    ].join(' ')}
                    title={buttonTitle}
                    onClick={() =>
                      setActive({
                        id: item.id,
                        code: item.iconCode,
                        title: item.name,
                        description: item.description,
                        awardedAt: item.earnedAt,
                        categoryLabel: item.categoryLabel,
                        owned,
                      })
                    }
                  >
                    <div className={owned ? 'shine-wrap flip-y' : ''}>
                      <BadgeIcon code={item.iconCode ?? ''} earned={owned} size={52} />
                    </div>
                    <div className="badge-name" style={{ marginTop: 4 }}>
                      {item.name}
                    </div>
                    {!owned && remaining != null && (
                      <div style={{ marginTop: 2, fontSize: 12, color: '#7b5a40' }}>남은 목표 {remaining}</div>
                    )}
                  </button>
                )
              })}
            </div>
          </section>
        )
      })}

      {active && (
        <BadgeDetailModal
          code={active.code}
          title={active.title}
          awardedAt={active.awardedAt}
          description={active.description}
          categoryLabel={active.categoryLabel}
          badgeId={active.id}
          canDisplay={active.owned}
          displayedBadgeId={displayedBadgeId}
          onDisplayChange={onDisplayChange}
          displayLoading={displayLoading}
          displayError={displayError}
          onClose={() => setActive(null)}
        />
      )}
    </div>
  )
}
