import { useCallback, useEffect, useMemo, useState } from 'react'
import ModalFrame from './ModalFrame'
import { cooktestAPI, type UserCookEvent, type UserCookPost } from '../api/cooktest'
import { formatCookUserDisplay, formatCookUserHandle } from '../utils/cooktest'
import CookTestPostModal from './CookTestPostModal'
import { usersAPI } from '../api/users'
import { BadgeIcon } from './badges/BadgeSet'
import { badgeMetaById } from '../data/badges'

type Props = {
  userId: number | string
  userName?: string
  onClose: () => void
  currentUserId?: string
  isLoggedIn: boolean
  onRequireLogin: () => void
}

export default function UserCookPostsModal({ userId, userName, onClose, currentUserId, isLoggedIn, onRequireLogin }: Props) {
  const [posts, setPosts] = useState<UserCookPost[]>([])
  const [events, setEvents] = useState<UserCookEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activePost, setActivePost] = useState<UserCookPost | null>(null)
  const [likedSet, setLikedSet] = useState<Set<number>>(new Set())
  const [pendingLikes, setPendingLikes] = useState<Set<number>>(new Set())
  const [displayedBadgeId, setDisplayedBadgeId] = useState<number | null>(null)

  useEffect(() => {
    let cancelled = false
    const fetchPosts = async () => {
      setLoading(true)
      setError(null)
      try {
        const { posts: postData, events: eventData } = await cooktestAPI.listUserPosts(userId)
        if (cancelled) return
        const normalized = Array.isArray(postData) ? [...postData] : []
        normalized.sort((a, b) => Number(b?.likes ?? 0) - Number(a?.likes ?? 0))
        setPosts(normalized)
        setEvents(Array.isArray(eventData) ? eventData : [])
      } catch (e: any) {
        if (cancelled) return
        setPosts([])
        setEvents([])
        setError(e?.message ?? '사용자 게시글을 불러오지 못했어요.')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetchPosts()
    return () => {
      cancelled = true
    }
  }, [userId])

  useEffect(() => {
    let cancelled = false
    const loadBadge = async () => {
      try {
        const { badge_id } = await usersAPI.getDisplayedBadge(userId)
        if (!cancelled) {
          setDisplayedBadgeId(badge_id ?? null)
        }
      } catch {
        if (!cancelled) setDisplayedBadgeId(null)
      }
    }
    loadBadge()
    return () => {
      cancelled = true
    }
  }, [userId])

  useEffect(() => {
    const liked = new Set<number>()
    posts.forEach(p => {
      if (p.liked_by_me) liked.add(p.post_id)
    })
    setLikedSet(liked)
  }, [posts])

  const stats = useMemo(() => {
    const eventIds = new Set<number>()
    if (events.length) {
      events.forEach(ev => eventIds.add(Number(ev.event_id)))
    } else {
      posts.forEach(p => eventIds.add(Number(p.event_id)))
    }
    return { postCount: posts.length, eventCount: eventIds.size }
  }, [posts, events])

  const eventMap = useMemo(() => {
    const map = new Map<number, UserCookEvent>()
    events.forEach(ev => map.set(Number(ev.event_id), ev))
    return map
  }, [events])

  const isEventClosed = useCallback(
    (eventId: number) => {
      const ev = eventMap.get(Number(eventId))
      if (!ev || !ev.end_date) return false
      const end = new Date(ev.end_date).getTime()
      return Number.isFinite(end) && end < Date.now()
    },
    [eventMap],
  )

  const toggleLike = async (post: UserCookPost) => {
    if (!isLoggedIn) {
      onRequireLogin()
      return
    }
    if (isEventClosed(post.event_id)) return
    const postId = post.post_id
    if (pendingLikes.has(postId)) return
    const liked = likedSet.has(postId)
    setPendingLikes(prev => new Set(prev).add(postId))
    setLikedSet(prev => {
      const next = new Set(prev)
      if (liked) next.delete(postId)
      else next.add(postId)
      return next
    })
    setPosts(prev =>
      prev.map(p =>
        p.post_id === postId ? { ...p, likes: Math.max(0, Number(p.likes ?? 0) + (liked ? -1 : 1)), liked_by_me: !liked } : p,
      ),
    )
    try {
      if (liked) await cooktestAPI.unlikePost(postId)
      else await cooktestAPI.likePost(postId)
    } catch (e: any) {
      const msg = e?.message ?? '좋아요 처리에 실패했어요.'
      setError(msg)
      setLikedSet(prev => {
        const next = new Set(prev)
        if (liked) next.add(postId)
        else next.delete(postId)
        return next
      })
      setPosts(prev =>
        prev.map(p =>
          p.post_id === postId ? { ...p, likes: Math.max(0, Number(p.likes ?? 0) + (liked ? 1 : -1)), liked_by_me: liked } : p,
        ),
      )
    } finally {
      setPendingLikes(prev => {
        const next = new Set(prev)
        next.delete(postId)
        return next
      })
    }
  }

  const label = formatCookUserDisplay(userId, userName)
  const handle = formatCookUserHandle(userId)

  return (
    <ModalFrame onClose={onClose} title={`${handle}의 게시글`}>
      <div className="user-post-panel">
        <div className="user-post-panel__header">
          <div>
            <div className="user-post-panel__title">
              {displayedBadgeId && badgeMetaById[displayedBadgeId]?.iconCode && (
                <span className="user-post-panel__badge" aria-hidden>
                  <BadgeIcon code={badgeMetaById[displayedBadgeId].iconCode} earned size={20} />
                </span>
              )}
              {label && <span>{label} </span>}
              <span className="user-handle">{handle}</span>
            </div>
            <div className="user-post-panel__meta">작성된 게시글 {stats.postCount}건 · 참여한 이벤트 {stats.eventCount}개</div>
          </div>
        </div>
        {loading && <div className="hint">불러오는 중…</div>}
        {error && <div className="error">{error}</div>}
        {!loading && !error && (
          posts.length === 0 ? (
            <div className="hint">게시글이 없습니다.</div>
          ) : (
            <div className="user-post-list">
              {posts.map(post => {
                const liked = likedSet.has(post.post_id)
                const disabled = pendingLikes.has(post.post_id) || isEventClosed(post.event_id)
                return (
                  <article
                    key={`${post.event_id}-${post.post_id}`}
                    className="user-post-card"
                    role="button"
                    tabIndex={0}
                    onClick={() => setActivePost(post)}
                    onKeyDown={e => {
                      if (e.key === 'Enter' || e.key === ' ') setActivePost(post)
                    }}
                  >
                    <div className="user-post-card__head">
                      <span className="user-post-card__event">{post.event_name ?? `이벤트 #${post.event_id}`}</span>
                      <span className="user-post-card__likes">❤️ {post.likes}</span>
                    </div>
                    <div className="user-post-card__title">{post.content_title}</div>
                    <div className="user-post-card__meta">{fmt(post.created_at)}</div>
                    <div className="user-post-card__body">{post.content_text}</div>
                    <div className="feed-actions" style={{ marginTop: 8 }}>
                      <button
                        className={`heart-btn ${liked ? 'on' : ''} ${pendingLikes.has(post.post_id) ? 'pulse' : ''}`}
                        onClick={e => {
                          e.stopPropagation()
                          toggleLike(post)
                        }}
                        aria-pressed={liked}
                        disabled={disabled}
                      >
                        <span className="heart-icon" aria-hidden>
                          {liked ? '❤' : '♡'}
                        </span>
                        <span className="heart-count">{post.likes}</span>
                      </button>
                    </div>
                  </article>
                )
              })}
            </div>
          )
        )}
        {!loading && !error && events.length > 0 && (
          <div className="user-event-list">
            <div className="user-event-list__title">참여한 대회</div>
            <ul>
              {events.map(ev => (
                <li key={ev.event_id} className="user-event-item">
                  <div className="user-event-name">{ev.event_name}</div>
                  <div className="user-event-dates">{formatEventRange(ev.start_date, ev.end_date)}</div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {activePost && (
        <CookTestPostModal
          eventId={Number(activePost.event_id)}
          postId={activePost.post_id}
          initial={activePost}
          currentUserId={currentUserId}
          allowOwnerActions={false}
          onClose={() => setActivePost(null)}
        />
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

function formatEventRange(start?: string, end?: string) {
  const toDate = (value?: string) => {
    if (!value) return ''
    try {
      return new Date(value).toLocaleDateString()
    } catch {
      return value
    }
  }
  const startLabel = toDate(start)
  const endLabel = toDate(end)
  if (startLabel && endLabel) return `${startLabel} ~ ${endLabel}`
  return startLabel || endLabel || '기간 미정'
}
