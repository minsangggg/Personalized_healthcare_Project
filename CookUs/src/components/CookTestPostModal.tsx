import { useEffect, useState } from 'react'
import ModalFrame from './ModalFrame'
import { cooktestAPI, type CookPost } from '../api/cooktest'

type Props = {
  eventId: number
  postId: number
  onClose: () => void
  initial?: CookPost | null
}

export default function CookTestPostModal({ eventId, postId, onClose, initial }: Props) {
  const [post, setPost] = useState<CookPost | null>(initial ?? null)
  const [loading, setLoading] = useState(!initial)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (initial) return
    (async () => {
      try {
        setLoading(true)
        const p = await cooktestAPI.getPost(eventId, postId)
        setPost(p)
      } catch (e: any) {
        setError(e?.message ?? '불러오기 실패')
      } finally {
        setLoading(false)
      }
    })()
  }, [eventId, postId, initial])

  return (
    <ModalFrame onClose={onClose} title={post?.content_title ?? '게시글 상세'}>
      <div style={{ display:'flex', flexDirection:'column', gap:12 }}>
        {loading && <div className="hint">불러오는 중…</div>}
        {error && <div className="error">{error}</div>}
        {post && (
          <article className="feed-card" style={{ boxShadow:'none' }}>
            <div className="feed-head">
              <div className="feed-title">{post.content_title}</div>
              <div className="feed-meta">사용자 #{post.user_id} · {fmt(post.created_at)}</div>
            </div>
            {(post.img_urls && post.img_urls.length > 0 ? post.img_urls : (post.img_url ? [post.img_url] : [])).map((u, idx) => (
              <img key={idx} src={u} alt={`post-${idx}`} className="feed-image" />
            ))}
            <div className="feed-body" style={{ whiteSpace:'pre-wrap' }}>{post.content_text}</div>
          </article>
        )}
      </div>
    </ModalFrame>
  )
}

function fmt(s: string) {
  try { return new Date(s).toLocaleString() } catch { return s }
}
