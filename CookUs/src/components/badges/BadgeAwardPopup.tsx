import { useMemo } from 'react'
import type { NotificationRow } from '../../api/notifications'
import { badgeCategoryLabels, badgeMetaById } from '../../data/badges'
import { BadgeIcon } from './BadgeSet'
import './BadgeAwardPopup.css'

type Props = {
  notification: NotificationRow
  onClose: () => void
}

export default function BadgeAwardPopup({ notification, onClose }: Props) {
  const badgeId = notification.related_id ?? undefined

  const meta = useMemo(() => (badgeId ? badgeMetaById[badgeId] : undefined), [badgeId])

  const heading = notification.title || meta?.description || '새 뱃지를 획득했어요!'
  const sub = notification.body || '열심히 활동한 만큼 보상이 도착했어요.'

  return (
    <div className="badge-award-overlay" role="dialog" aria-modal="true" aria-live="assertive">
      <div className="badge-award-card">
        <button className="badge-award-close" aria-label="닫기" onClick={onClose}>
          ×
        </button>
        <div className="badge-award-confetti" aria-hidden />
        <div className="badge-award-icon-wrap">
          <div className="badge-award-flip">
            <BadgeIcon code={meta?.iconCode ?? ''} earned size={96} />
          </div>
        </div>
        <p className="badge-award-label">New Badge</p>
        <h3 className="badge-award-title">{heading}</h3>
        <p className="badge-award-desc">{sub}</p>
        {(meta?.target || meta?.category) && (
          <p className="badge-award-meta">
            {meta?.target ? `목표: ${meta.target}` : null}
            {meta?.target && meta?.category ? ' · ' : ''}
            {meta?.category ? `카테고리: ${badgeCategoryLabels[meta.category]}` : null}
          </p>
        )}
      </div>
    </div>
  )
}
