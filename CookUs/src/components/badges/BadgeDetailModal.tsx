import ModalFrame from '../ModalFrame'
import { BadgeIcon, LABELS_KO } from './BadgeSet'
type Props = {
  code?: string
  title: string
  onClose: () => void
  awardedAt?: string | null
  description?: string
  categoryLabel?: string
  badgeId?: number
  canDisplay?: boolean
  displayedBadgeId?: number | null
  onDisplayChange?: (badgeId: number | null) => Promise<boolean>
  displayLoading?: boolean
  displayError?: string | null
}

export default function BadgeDetailModal({
  code,
  title,
  onClose,
  awardedAt,
  description,
  categoryLabel,
  badgeId,
  canDisplay,
  displayedBadgeId,
  onDisplayChange,
  displayLoading,
  displayError,
}: Props) {
  const meta = code ? (LABELS_KO as any)[code] : null
  const awardedStr = awardedAt ? new Date(awardedAt).toLocaleString() : null
  const isDisplayed = canDisplay && badgeId != null && displayedBadgeId === badgeId

  const handleDisplayToggle = async () => {
    if (!onDisplayChange || !canDisplay || badgeId == null) return
    await onDisplayChange(isDisplayed ? null : badgeId)
  }

  return (
    <ModalFrame onClose={onClose} title={title}>
      <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', gap: 16, alignItems: 'center', overflow: 'hidden' }}>
        <div style={{ display: 'grid', placeItems: 'center' }}>
          <div className="badge-spin-glow">
            <BadgeIcon code={code ?? ''} earned size={96} />
          </div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {categoryLabel && <div style={{ color: '#7a513a', fontWeight: 700 }}>{categoryLabel}</div>}
          {description && <div style={{ whiteSpace: 'pre-wrap' }}>{description}</div>}
          {awardedStr ? (
            <div style={{ color: '#1f6a55', fontWeight: 600 }}>획득일 {awardedStr}</div>
          ) : (
            <div style={{ color: '#9b2f2f' }}>아직 획득하지 않았어요.</div>
          )}
          {meta?.label && <div style={{ fontSize: 12, color: '#9ca3af' }}>{meta.label}</div>}
          {canDisplay && onDisplayChange && (
            <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 6 }}>
              <button
                type="button"
                className="btn primary"
                onClick={handleDisplayToggle}
                disabled={displayLoading}
              >
                {isDisplayed ? '프로필에서 숨기기' : '프로필에 표시'}
              </button>
              {displayError && (
                <div style={{ color: '#b91c1c', fontSize: 12 }}>
                  {displayError}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </ModalFrame>
  )
}
