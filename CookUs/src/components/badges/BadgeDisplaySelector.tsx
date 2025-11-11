import ModalFrame from '../ModalFrame'
import { BadgeIcon } from './BadgeSet'
import type { EarnedBadge } from '../../api/badges'
import { badgeMetaById } from '../../data/badges'
import './BadgeDisplaySelector.css'

type Props = {
  earnedBadges: EarnedBadge[]
  displayedBadgeId: number | null
  onSelect: (badgeId: number | null) => Promise<boolean>
  loading?: boolean
  error?: string | null
  onClose: () => void
}

export default function BadgeDisplaySelector({
  earnedBadges,
  displayedBadgeId,
  onSelect,
  loading,
  error,
  onClose,
}: Props) {
  const handlePick = async (badgeId: number | null) => {
    const ok = await onSelect(badgeId)
    if (ok) onClose()
  }

  return (
    <ModalFrame title="대표 배지 선택" onClose={onClose}>
      <div className="badge-display-panel">
        <div className="badge-display-label">표시할 배지</div>
        <div className="badge-display-list">
          <button
            type="button"
            className={`badge-display-item${displayedBadgeId == null ? ' active' : ''}`}
            onClick={() => handlePick(null)}
            disabled={loading}
          >
            <span className="badge-display-check">{displayedBadgeId == null ? '●' : '○'}</span>
            대표 없음
          </button>
          {earnedBadges.map(b => {
            const meta = badgeMetaById[b.badge_id]
            return (
              <button
                key={b.badge_id}
                type="button"
                className={`badge-display-item${displayedBadgeId === b.badge_id ? ' active' : ''}`}
                onClick={() => handlePick(b.badge_id)}
                disabled={loading}
              >
                <BadgeIcon code={meta?.iconCode ?? ''} earned size={28} />
                <span>{b.name}</span>
              </button>
            )
          })}
        </div>
        {error && <div className="badge-display-error">{error}</div>}
      </div>
    </ModalFrame>
  )
}
