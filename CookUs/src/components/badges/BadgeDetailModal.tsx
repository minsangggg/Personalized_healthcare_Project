import ModalFrame from '../ModalFrame'
import { BadgeIcon, LABELS_KO } from './BadgeSet'

type Props = {
  code?: string
  title: string
  onClose: () => void
  awardedAt?: string | null
  description?: string
  categoryLabel?: string
}

export default function BadgeDetailModal({ code, title, onClose, awardedAt, description, categoryLabel }: Props) {
  const meta = code ? (LABELS_KO as any)[code] : null
  const awardedStr = awardedAt ? new Date(awardedAt).toLocaleString() : null

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
            <div style={{ color: '#1f6a55', fontWeight: 600 }}>획득일: {awardedStr}</div>
          ) : (
            <div style={{ color: '#9b2f2f' }}>아직 획득하지 않았어요.</div>
          )}
          {meta?.label && <div style={{ fontSize: 12, color: '#9ca3af' }}>{meta.label}</div>}
        </div>
      </div>
    </ModalFrame>
  )
}

