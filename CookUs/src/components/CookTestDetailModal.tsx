import { useEffect, useState } from 'react'
import ModalFrame from './ModalFrame'
import { cooktestAPI, type CookPost, type EventDetail } from '../api/cooktest'
import CreateCookTestPostModal from './CreateCookTestPostModal'
import CookTestPostModal from './CookTestPostModal'

type Props = {
  eventId: number
  onClose: () => void
  isLoggedIn: boolean
  onRequireLogin: () => void
}

export default function CookTestDetailModal({ eventId, onClose, isLoggedIn, onRequireLogin }: Props) {
  const [event, setEvent] = useState<EventDetail | null>(null)
  const [posts, setPosts] = useState<CookPost[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [likedSet, setLikedSet] = useState<Set<number>>(new Set())
  const [activePost, setActivePost] = useState<CookPost | null>(null)

  const load = async () => {
    try {
      setLoading(true)
      const [ev, ps] = await Promise.all([
        cooktestAPI.getEvent(eventId),
        cooktestAPI.listPosts(eventId),
      ])
      setEvent(ev)
      setPosts(ps)
    } catch (e: any) {
      setError(e?.message ?? '불러오기 실패')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [eventId])

  const handleLike = async (postId: number) => {
    if (likedSet.has(postId)) return
    try {
      const { likes } = await cooktestAPI.likePost(postId)
      setPosts(prev => prev.map(p => p.post_id === postId ? { ...p, likes } : p))
      setLikedSet(prev => new Set(prev).add(postId))
    } catch {}
  }

  const ensureLoginAndOpenCreate = () => {
    if (!isLoggedIn) return onRequireLogin()
    setShowCreate(true)
  }

  return (
    <ModalFrame onClose={onClose} title={event?.event_name ?? '대회 상세'}>
      <div style={{ display:'flex', flexDirection:'column', gap:12 }}>
        {event && (
          <div>
            <div style={{ fontSize:18, fontWeight:700 }}>{event.event_name}</div>
            <div style={{ color:'#666', marginTop:4 }}>{event.event_description}</div>
            <div style={{ color:'#888', marginTop:6 }}>{fmt(event.start_date)} ~ {fmt(event.end_date)}</div>
          </div>
        )}

        <div style={{ display:'flex', justifyContent:'flex-end' }}>
          <button className="btn" onClick={ensureLoginAndOpenCreate}>참가하기</button>
        </div>

        {loading && <div className="hint">피드를 불러오는 중…</div>}
        {error && <div className="error">{error}</div>}

        <div style={{ display:'flex', flexDirection:'column', gap:12 }}>
          {posts.map(p => (
            <article key={p.post_id} className="feed-card">
              <div className="feed-head">
                <div className="feed-title" onClick={() => setActivePost(p)} style={{ cursor:'pointer' }}>{p.content_title}</div>
                <div className="feed-meta">{p.user_name ?? `사용자 #${p.user_id}`} · {fmt(p.created_at)}</div>
              </div>
              <div className="feed-body">{p.content_text}</div>
              {p.img_url && (
                <img src={p.img_url} alt="post" className="feed-image" onClick={() => setActivePost(p)} style={{ cursor:'pointer' }} />
              )}
              <div className="feed-actions">
                <button className="btn ghost" onClick={() => handleLike(p.post_id)}>좋아요 {p.likes}</button>
              </div>
            </article>
          ))}
          {!loading && !posts.length && (
            <div className="hint">아직 게시글이 없습니다. 첫 참가자가 되어보세요!</div>
          )}
        </div>
      </div>

      {showCreate && (
        <CreateCookTestPostModal
          eventId={eventId}
          onClose={() => setShowCreate(false)}
          onCreated={() => { setShowCreate(false); load() }}
        />
      )}
      {activePost && (
        <CookTestPostModal
          eventId={eventId}
          postId={activePost.post_id}
          initial={activePost}
          onClose={() => setActivePost(null)}
        />
      )}
    </ModalFrame>
  )
}

function fmt(s: string) {
  try { return new Date(s).toLocaleString() } catch { return s }
}

