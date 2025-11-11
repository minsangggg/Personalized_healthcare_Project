import ModalFrame from '../ModalFrame'
import { BadgeIcon, LABELS_KO } from './BadgeSet'

type Props = {
  code: string
  onClose: () => void
  awardedAt?: string | null
  description?: string
  title?: string
}

export default function BadgeDetailModal({ code, onClose, awardedAt, description, title }: Props) {
  const meta = (LABELS_KO as any)[code] || { label: code, group: '' }
  const awardedStr = awardedAt ? new Date(awardedAt).toLocaleString() : null
  const heading = title || meta.label || code

  return (
    <ModalFrame onClose={onClose} title={heading}>
      <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', gap: 16, alignItems: 'center', overflow: 'hidden' }}>
        <div style={{ display: 'grid', placeItems: 'center' }}>
          <div className="badge-spin-glow">
            <BadgeIcon code={code} earned size={96} />
          </div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {meta.group && <div style={{ color: '#7a513a', fontWeight: 700 }}>{meta.group}</div>}
          {description && <div style={{ whiteSpace: 'pre-wrap' }}>{description}</div>}
          {awardedStr ? (
            <div style={{ color: '#1f6a55', fontWeight: 600 }}>획득일: {awardedStr}</div>
          ) : (
            <div style={{ color: '#9b2f2f' }}>아직 획득하지 않았어요.</div>
          )}
        </div>
      </div>
    </ModalFrame>
  )
}

