import { useEffect, useState } from 'react'
import ModalFrame from './ModalFrame'
import { cooktestAPI, type CookPost } from '../api/cooktest'

type Props = {
  eventId: number
  postId: number
  onClose: () => void
  initial?: CookPost | null
  currentUserId?: string
  onRequestEdit?: (post: CookPost) => void
  onDeleted?: () => void
  allowOwnerActions?: boolean
}

export default function CookTestPostModal({
  eventId,
  postId,
  onClose,
  initial,
  currentUserId,
  onRequestEdit,
  onDeleted,
  allowOwnerActions = true,
}: Props) {
  const [post, setPost] = useState<CookPost | null>(initial ?? null)
  const [loading, setLoading] = useState(!initial)
  const [error, setError] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)

  useEffect(() => {
    if (initial) return
    ;(async () => {
      try {
        setLoading(true)
        const fresh = await cooktestAPI.getPost(eventId, postId)
        setPost(fresh)
      } catch (e: any) {
        setError(e?.message ?? '불러오기 실패')
      } finally {
        setLoading(false)
      }
    })()
  }, [eventId, postId, initial])

  const isOwner = post && currentUserId && String(post.user_id) === String(currentUserId)
  const canModify = Boolean(isOwner && allowOwnerActions)

  const handleDelete = async () => {
    if (!post || deleting) return
    try {
      setDeleting(true)
      await cooktestAPI.deletePost(eventId, postId)
      onDeleted?.()
      onClose()
    } catch (e: any) {
      setError(e?.message ?? '삭제 실패')
    } finally {
      setDeleting(false)
    }
  }

  const images = post
    ? post.img_urls && post.img_urls.length > 0
      ? post.img_urls
      : post.img_url
        ? [post.img_url]
        : []
    : []

  return (
    <ModalFrame onClose={onClose} title={post?.content_title ?? '게시글 보기'}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {loading && <div className="hint">불러오는 중...</div>}
        {error && <div className="error">{error}</div>}
        {post && (
          <article className="feed-card" style={{ boxShadow: 'none' }}>
            {canModify && (
              <div style={{ display: 'flex', gap: 8, marginBottom: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                <button className="btn ghost" onClick={() => onRequestEdit?.(post)} disabled={deleting}>
                  수정
                </button>
                <button
                  className="btn ghost"
                  style={{ color: '#b91c1c', borderColor: '#fca5a5' }}
                  onClick={() => setShowConfirm(true)}
                  disabled={deleting}
                >
                  삭제
                </button>
              </div>
            )}
            <div className="feed-head">
              <div className="feed-title">{post.content_title}</div>
              <div className="feed-meta">사용자 #{post.user_id} · {fmt(post.created_at)}</div>
            </div>
            {images.map((src, idx) => (
              <img key={idx} src={src} alt="" className="feed-image" loading="lazy" />
            ))}
            <div className="feed-body" style={{ whiteSpace: 'pre-wrap' }}>
              {post.content_text}
            </div>
          </article>
        )}
      </div>

      {showConfirm && (
        <div className="modal-confirm-backdrop" role="dialog" aria-modal="true">
          <div className="modal-confirm">
            <p>게시글을 삭제할까요?</p>
            {error && <div className="error" style={{ marginBottom: 8 }}>{error}</div>}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
              <button className="btn ghost" onClick={() => setShowConfirm(false)} disabled={deleting}>
                취소
              </button>
              <button
                className="btn"
                style={{ background: '#dc2626', borderColor: '#b91c1c', color: '#fff' }}
                onClick={handleDelete}
                disabled={deleting}
              >
                {deleting ? '삭제 중...' : '삭제'}
              </button>
            </div>
          </div>
        </div>
      )}
    </ModalFrame>
  )
}

function fmt(s: string) {
  try {
    return new Date(s).toLocaleString()
  } catch {
    return s
  }
}

