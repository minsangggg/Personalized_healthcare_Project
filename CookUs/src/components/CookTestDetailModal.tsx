import { useEffect, useMemo, useState } from 'react'
import ModalFrame from './ModalFrame'
import { cooktestAPI, type CookPost, type EventDetail } from '../api/cooktest'
import CreateCookTestPostModal from './CreateCookTestPostModal'
import CookTestPostModal from './CookTestPostModal'
import EditCookTestPostModal from './EditCookTestPostModal'

type FilterView = 'all' | 'liked' | 'mine'

type Props = {
  eventId: number
  onClose: () => void
  isLoggedIn: boolean
  onRequireLogin: () => void
  userId?: string
}

export default function CookTestDetailModal({
  eventId,
  onClose,
  isLoggedIn,
  onRequireLogin,
  userId,
}: Props) {
  const [event, setEvent] = useState<EventDetail | null>(null)
  const [allPosts, setAllPosts] = useState<CookPost[]>([])
  const [posts, setPosts] = useState<CookPost[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [activePost, setActivePost] = useState<CookPost | null>(null)
  const [editingPost, setEditingPost] = useState<CookPost | null>(null)
  const [likedSet, setLikedSet] = useState<Set<number>>(new Set())
  const [pendingLikes, setPendingLikes] = useState<Set<number>>(new Set())
  const [limitMessage, setLimitMessage] = useState<string | null>(null)
  const [filterView, setFilterView] = useState<FilterView>('all')
  const [showPosts, setShowPosts] = useState(true)
  const isEventClosed = useMemo(() => {
    if (!event) return false
    const end = new Date(event.end_date)
    const now = new Date()
    return now.getTime() > end.getTime()
  }, [event])

  const sortedPosts = useMemo(() => {
    const base = [...posts].sort((a, b) => {
      if (b.likes !== a.likes) return b.likes - a.likes
      return a.post_id - b.post_id
    })
    return isEventClosed ? base : posts
  }, [posts, isEventClosed])

  const uniquePodiumEntries = useMemo(() => {
    if (!isEventClosed) return []
    const sortedAll = [...allPosts].sort((a, b) => {
      if (b.likes !== a.likes) return b.likes - a.likes
      return a.post_id - b.post_id
    })
    const seen = new Set<string>()
    return sortedAll.filter((p) => {
      const key = String(p.user_id)
      if (seen.has(key)) return false
      seen.add(key)
      return true
    })
  }, [allPosts, isEventClosed])

  const podiumByRank = useMemo(() => {
    const map = new Map<number, CookPost[]>()
    if (!isEventClosed) return map
    let currentRank = 1
    let index = 0
    while (index < uniquePodiumEntries.length && currentRank <= 3) {
      let tieEnd = index + 1
      while (
        tieEnd < uniquePodiumEntries.length &&
        uniquePodiumEntries[tieEnd].likes === uniquePodiumEntries[index].likes
      ) {
        tieEnd++
      }
      map.set(currentRank, uniquePodiumEntries.slice(index, tieEnd))
      const tieSize = tieEnd - index
      currentRank += tieSize
      index = tieEnd
    }
    return map
  }, [uniquePodiumEntries, isEventClosed])

  const loadPosts = async (view: FilterView) => {
    setError(null)
    try {
      setLoading(true)
      const data = await cooktestAPI.listPosts(eventId, view)
      if (view === 'all') {
        setAllPosts(data)
      }
      setPosts(data)
    } catch (e: any) {
      setError(e?.message ?? '불러오기 실패')
    } finally {
      setLoading(false)
    }
  }

  const initialize = async () => {
    setError(null)
    try {
      setLoading(true)
      const [ev, list] = await Promise.all([
        cooktestAPI.getEvent(eventId),
        cooktestAPI.listPosts(eventId, 'all'),
      ])
      setEvent(ev)
      setAllPosts(list)
      setPosts(list)
    } catch (e: any) {
      setError(e?.message ?? '불러오기 실패')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    initialize()
  }, [eventId])

  useEffect(() => {
    setShowPosts(!isEventClosed)
  }, [eventId, isEventClosed])

  useEffect(() => {
    if (filterView === 'all') {
      setPosts(allPosts)
      return
    }
    // require login for filtered views
    if (!isLoggedIn) {
      setFilterView('all')
      onRequireLogin()
      return
    }
    loadPosts(filterView)
  }, [filterView, isLoggedIn, allPosts])

  useEffect(() => {
    let disposed = false
    if (!isLoggedIn) {
      setLikedSet(new Set())
      return
    }
    ;(async () => {
      try {
        const likedIds = await cooktestAPI.myLikes(eventId)
        if (!disposed) setLikedSet(new Set(likedIds))
      } catch {
        if (!disposed) setLikedSet(new Set())
      }
    })()
    return () => {
      disposed = true
    }
  }, [eventId, isLoggedIn])

  const myPostCount = useMemo(() => {
    if (!userId) return 0
    return allPosts.filter(p => String(p.user_id) === String(userId)).length
  }, [allPosts, userId])

  const hasReachedLimit = isLoggedIn && !!userId && myPostCount >= 3

  useEffect(() => {
    if (!isEventClosed && !hasReachedLimit) setLimitMessage(null)
  }, [hasReachedLimit, isEventClosed])

  const ensureLoginAndOpenCreate = () => {
    if (!isLoggedIn) return onRequireLogin()
    if (isEventClosed) {
      setLimitMessage('참여 기간이 지난 대회입니다')
      return
    }
    if (hasReachedLimit) {
      setLimitMessage('이미 3번을 다 참여하셨어요')
      return
    }
    setShowCreate(true)
  }

  const handleFilterChange = (value: FilterView) => {
    if (value !== 'all' && !isLoggedIn) {
      onRequireLogin()
      return
    }
    setFilterView(value)
  }

  const refreshAfterChange = async () => {
    await initialize()
    if (filterView !== 'all') {
      await loadPosts(filterView)
    }
  }

  const refreshSinglePost = async (postId: number) => {
    try {
      const fresh = await cooktestAPI.getPost(eventId, postId)
      setActivePost(fresh)
    } catch {
      setActivePost(null)
    }
  }

  const toggleLike = async (postId: number, liked: boolean) => {
    if (!isLoggedIn) return onRequireLogin()
    const target = posts.find(p => p.post_id === postId)
    const prevLikes = target?.likes ?? 0
    const delta = liked ? -1 : 1

    setPendingLikes(prev => new Set(prev).add(postId))
    setPosts(prev =>
      prev.map(p =>
        p.post_id === postId ? { ...p, likes: Math.max(0, p.likes + delta) } : p
      )
    )
    setLikedSet(prev => {
      const next = new Set(prev)
      if (liked) next.delete(postId)
      else next.add(postId)
      return next
    })

    try {
      const { likes } = liked
        ? await cooktestAPI.unlikePost(postId)
        : await cooktestAPI.likePost(postId)
      setPosts(prev =>
        prev.map(p => (p.post_id === postId ? { ...p, likes } : p))
      )
      if (filterView === 'liked' && liked) {
        setPosts(prev => prev.filter(p => p.post_id !== postId))
      }
      if (filterView === 'all') {
        setAllPosts(prev =>
          prev.map(p => (p.post_id === postId ? { ...p, likes } : p))
        )
      }
    } catch {
      setPosts(prev =>
        prev.map(p => (p.post_id === postId ? { ...p, likes: prevLikes } : p))
      )
      setLikedSet(prev => {
        const next = new Set(prev)
        if (liked) next.add(postId)
        else next.delete(postId)
        return next
      })
    } finally {
      setPendingLikes(prev => {
        const next = new Set(prev)
        next.delete(postId)
        return next
      })
    }
  }

  return (
    <ModalFrame onClose={onClose} title={event?.event_name ?? '요리 대회'}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {event && (
          <div>
            <div style={{ fontSize: 18, fontWeight: 700 }}>{event.event_name}</div>
            <div style={{ color: '#666', marginTop: 4 }}>{event.event_description}</div>
            <div style={{ color: '#888', marginTop: 6 }}>
              {fmt(event.start_date)} ~ {fmt(event.end_date)}
            </div>
            {isEventClosed && (
              <div className="podium-wrap">
                {['silver', 'gold', 'bronze'].map((tier, idx) => {
                  const rankNumber = tier === 'gold' ? 1 : tier === 'silver' ? 2 : 3
                  const group = podiumByRank.get(rankNumber) || []
                  const label = group && group.length
                    ? group.map(p => `#${p.user_id}`).join(', ')
                    : '빈자리'
                  const rankLabel = `${rankNumber}위`
                  return (
                    <div key={tier} className={`podium-tier podium-${tier}`}>
                      <span className="podium-rank">{rankLabel}</span>
                      <span className="podium-user">{label}</span>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )}

        <div className="cooktest-actions">
          <div className="cooktest-actions-right">
            <button className="btn ghost toggle-btn" onClick={() => setShowPosts(p => !p)}>
              {showPosts ? '게시글 숨기기' : '게시글 보기'}
            </button>
            {!isEventClosed ? (
              <button className="btn" onClick={ensureLoginAndOpenCreate}>
                참가하기
              </button>
            ) : (
              <div className="cooktest-closed-tag">참여 기간이 지난 대회입니다</div>
            )}
            {limitMessage && <div className="limit-message">{limitMessage}</div>}
          </div>
        </div>

        {loading && <div className="hint">불러오는 중…</div>}
        {error && <div className="error">{error}</div>}

        {!showPosts && (
          <div className="hint">게시글 보기를 눌러 좋아요 순위 게시글을 확인하세요.</div>
        )}
        {showPosts && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div className="cooktest-filter-bar">
              <label className="cooktest-view-select">
                <span>보기</span>
                <select
                  value={filterView}
                  onChange={e => handleFilterChange(e.target.value as FilterView)}
                >
                  <option value="all">전체</option>
                  <option value="liked">내 좋아요</option>
                  <option value="mine">내 글</option>
                </select>
              </label>
              {filterView !== 'all' && <div className="hint small">조건에 맞는 게시글만 표시돼요.</div>}
            </div>
          {sortedPosts.map(p => {
            const liked = likedSet.has(p.post_id)
            const busy = pendingLikes.has(p.post_id)
            return (
              <article key={p.post_id} className="feed-card">
                <div className="feed-head">
                  <div
                    className="feed-title"
                    onClick={() => setActivePost(p)}
                    style={{ cursor: 'pointer' }}
                  >
                    {p.content_title}
                  </div>
                  <div className="feed-meta">
                    {p.user_name ?? `사용자 #${p.user_id}`} · {fmt(p.created_at)}
                  </div>
                </div>
                <div className="feed-body">{p.content_text}</div>
                {p.img_url && (
                  <img
                    src={p.img_url}
                    alt="post"
                    className="feed-image"
                    onClick={() => setActivePost(p)}
                    style={{ cursor: 'pointer' }}
                  />
                )}
                <div className="feed-actions">
                  <button
                    className={`heart-btn ${liked ? 'on' : ''} ${busy ? 'pulse' : ''}`}
                    onClick={() => toggleLike(p.post_id, liked)}
                    aria-pressed={liked}
                    disabled={busy || isEventClosed}
                  >
                    <span className="heart-icon" aria-hidden>{liked ? '♥' : '♡'}</span>
                    <span className="heart-count">{p.likes}</span>
                  </button>
                </div>
              </article>
            )
          })}
          {!loading && posts.length === 0 && (
            <div className="hint">조건에 맞는 게시글이 없어요.</div>
          )}
          </div>
        )}
      </div>

      {showCreate && (
        <CreateCookTestPostModal
          eventId={eventId}
          onClose={() => setShowCreate(false)}
          onCreated={async () => {
            setShowCreate(false)
            await refreshAfterChange()
          }}
        />
      )}
      {activePost && (
        <CookTestPostModal
          eventId={eventId}
          postId={activePost.post_id}
          initial={activePost}
          currentUserId={userId}
          onClose={() => setActivePost(null)}
          onRequestEdit={post => setEditingPost(post)}
          onDeleted={async () => {
            await refreshAfterChange()
          }}
        />
      )}
      {editingPost && (
        <EditCookTestPostModal
          eventId={eventId}
          post={editingPost}
          onClose={() => setEditingPost(null)}
          onSaved={async () => {
            const editedId = editingPost.post_id
            setEditingPost(null)
            await refreshAfterChange()
            await refreshSinglePost(editedId)
          }}
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
