import { useCallback, useEffect, useMemo, useState } from 'react'
import ModalFrame from './ModalFrame'
import { cooktestAPI, type CookPost, type EventDetail } from '../api/cooktest'
import CreateCookTestPostModal from './CreateCookTestPostModal'
import CookTestPostModal from './CookTestPostModal'
import EditCookTestPostModal from './EditCookTestPostModal'
import UserCookPostsModal from './UserCookPostsModal'
import { BadgeIcon } from './badges/BadgeSet'
import { badgeMetaById } from '../data/badges'
import { usersAPI } from '../api/users'

type FilterView = 'all' | 'liked' | 'mine'
type SortOption = 'latest' | 'likes'

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
  const [userBadgeMap, setUserBadgeMap] = useState<Record<string, number | null>>({})
  const [filterView, setFilterView] = useState<FilterView>('all')
  const [showPosts, setShowPosts] = useState(true)
  const [sortOption, setSortOption] = useState<SortOption>('latest')
  const [userPostsTarget, setUserPostsTarget] = useState<{ userId: number; userName?: string } | null>(null)

  const isEventClosed = useMemo(() => {
    if (!event) return false
    const end = new Date(event.end_date)
    const now = new Date()
    return now.getTime() > end.getTime()
  }, [event])

  const sortedPosts = useMemo(() => {
    const list = [...posts]
    if (sortOption === 'likes') {
      list.sort((a, b) => {
        if (b.likes !== a.likes) return b.likes - a.likes
        return a.post_id - b.post_id
      })
    } else {
      list.sort((a, b) => {
        const aTime = Date.parse(a.created_at)
        const bTime = Date.parse(b.created_at)
        if (Number.isFinite(bTime) && Number.isFinite(aTime) && bTime !== aTime) {
          return bTime - aTime
        }
        return b.post_id - a.post_id
      })
    }
    return list
  }, [posts, sortOption])

  useEffect(() => {
    const ids = Array.from(new Set(posts.map(p => String(p.user_id))))
    const missing = ids.filter(id => !(id in userBadgeMap))
    if (missing.length === 0) return
    let cancelled = false
    const loadBadges = async () => {
      const results = await Promise.all(
        missing.map(async id => {
          try {
            const { badge_id } = await usersAPI.getDisplayedBadge(id)
            return [id, badge_id ?? null] as [string, number | null]
          } catch {
            return [id, null] as [string, number | null]
          }
        }),
      )
      if (cancelled) return
      setUserBadgeMap(prev => {
        const next = { ...prev }
        for (const [id, badgeId] of results) {
          next[id] = badgeId
        }
        return next
      })
    }
    loadBadges()
    return () => {
      cancelled = true
    }
  }, [posts, userBadgeMap])

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
    return () => { disposed = true }
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
    try { setActivePost(await cooktestAPI.getPost(eventId, postId)) }
    catch { setActivePost(null) }
  }

  const toggleLike = async (postId: number, liked: boolean) => {
    if (!isLoggedIn) return onRequireLogin()
    const target = posts.find(p => p.post_id === postId)
    const prevLikes = target?.likes ?? 0
    const delta = liked ? -1 : 1

    setPendingLikes(prev => new Set(prev).add(postId))
    setPosts(prev => prev.map(p => p.post_id === postId ? { ...p, likes: Math.max(0, p.likes + delta) } : p))
    setLikedSet(prev => { const next = new Set(prev); if (liked) next.delete(postId); else next.add(postId); return next })

    try {
      const { likes } = liked ? await cooktestAPI.unlikePost(postId) : await cooktestAPI.likePost(postId)
      setPosts(prev => prev.map(p => (p.post_id === postId ? { ...p, likes } : p)))
      if (filterView === 'liked' && liked) setPosts(prev => prev.filter(p => p.post_id !== postId))
      if (filterView === 'all') setAllPosts(prev => prev.map(p => (p.post_id === postId ? { ...p, likes } : p)))
    } catch {
      setPosts(prev => prev.map(p => (p.post_id === postId ? { ...p, likes: prevLikes } : p)))
      setLikedSet(prev => { const next = new Set(prev); if (liked) next.add(postId); else next.delete(postId); return next })
    } finally {
      setPendingLikes(prev => { const next = new Set(prev); next.delete(postId); return next })
    }
  }

  const openUserPosts = (post: CookPost) => {
    setUserPostsTarget({ userId: post.user_id, userName: post.user_name })
  }

  return (
    <ModalFrame onClose={onClose} title={event?.event_name ?? '요리 대회'}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {event && (
          <div>
            <div style={{ fontSize: 18, fontWeight: 700 }}>{event.event_name}</div>
            <div style={{ color: '#666', marginTop: 4 }}>{event.event_description}</div>
            <div style={{ color: '#888', marginTop: 6 }}>{new Date(event.start_date).toLocaleString()} ~ {new Date(event.end_date).toLocaleString()}</div>
            {isEventClosed && (
              <div className="podium-wrap">
                {['silver', 'gold', 'bronze'].map((tier) => {
                  const rankNumber = tier === 'gold' ? 1 : tier === 'silver' ? 2 : 3
                  const group = podiumByRank.get(rankNumber) || []
                  const label = group && group.length ? group.map(p => `#${p.user_id}`).join(', ') : '빈자리'
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
            {isEventClosed && (
              <button className="btn ghost toggle-btn" onClick={() => setShowPosts(p => !p)}>
                {showPosts ? '게시글 숨기기' : '게시글 보기'}
              </button>
            )}
            {!isEventClosed ? (
              <button className="btn" onClick={ensureLoginAndOpenCreate}>참가하기</button>
            ) : (
              <div className="cooktest-closed-tag">참여 기간이 지난 대회입니다</div>
            )}
            {limitMessage && <div className="limit-message">{limitMessage}</div>}
          </div>
        </div>

        {loading && <div className="hint">불러오는 중…</div>}
        {error && <div className="error">{error}</div>}

        {!showPosts && isEventClosed && (<div className="hint">게시글 보기를 눌러 좋아요 순위 게시글을 확인하세요.</div>)}
        {(showPosts || !isEventClosed) && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div className="cooktest-filter-bar">
              <label className="cooktest-view-select">
                <span>보기</span>
                <select value={filterView} onChange={e => handleFilterChange(e.target.value as FilterView)}>
                  <option value="all">전체</option>
                  <option value="liked">내 좋아요</option>
                  <option value="mine">내 글</option>
                </select>
              </label>
              <label className="cooktest-view-select">
                <span>정렬</span>
                <select value={sortOption} onChange={e => setSortOption(e.target.value as SortOption)}>
                  <option value="latest">최신순</option>
                  <option value="likes">좋아요순</option>
                </select>
              </label>
              {filterView !== 'all' && <div className="hint small">조건에 맞는 게시글만 표시돼요.</div>}
            </div>
            {sortedPosts.map(p => {
              const liked = likedSet.has(p.post_id)
              const busy = pendingLikes.has(p.post_id)
              const userIdKey = String(p.user_id)
              const userBadgeIdFromMap = userBadgeMap[userIdKey]
              const userBadgeMeta = userBadgeIdFromMap ? badgeMetaById[userBadgeIdFromMap] : undefined
              return (
                <article key={p.post_id} className="feed-card">
                  <div className="feed-head">
                    <div className="feed-title" onClick={() => setActivePost(p)} style={{ cursor: 'pointer' }}>{p.content_title}</div>
                    <div className="feed-meta">
                      <button
                        type="button"
                        className="user-link"
                        onClick={() => openUserPosts(p)}
                      >
                        {userBadgeMeta?.iconCode && (
                          <span className="displayed-user-badge" aria-hidden>
                            <BadgeIcon code={userBadgeMeta.iconCode} earned size={20} />
                          </span>
                        )}
                        {p.user_name ?? `사용자 #${p.user_id}`}
                      </button>
                      <span> · {fmt(p.created_at)}</span>
                    </div>
                  </div>
                  <div className="feed-body">{p.content_text}</div>
                  {p.img_url && (
                    <img src={p.img_url} alt="post" className="feed-image" onClick={() => setActivePost(p)} style={{ cursor: 'pointer' }} />
                  )}
                  <div className="feed-actions">
                    <button className={`heart-btn ${liked ? 'on' : ''} ${busy ? 'pulse' : ''}`} onClick={() => toggleLike(p.post_id, liked)} aria-pressed={liked} disabled={busy || isEventClosed}>
                      <span className="heart-icon" aria-hidden>{liked ? '♥' : '♡'}</span>
                      <span className="heart-count">{p.likes}</span>
                    </button>
                  </div>
                </article>
              )
            })}
            {!loading && posts.length === 0 && (<div className="hint">조건에 맞는 게시글이 없어요.</div>)}
          </div>
        )}
      </div>

      {showCreate && (
        <CreateCookTestPostModal
          eventId={eventId}
          onClose={() => setShowCreate(false)}
          onCreated={async () => { setShowCreate(false); await refreshAfterChange() }}
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
          onDeleted={async () => { await refreshAfterChange() }}
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
      {userPostsTarget && (
        <UserCookPostsModal
          userId={userPostsTarget.userId}
          userName={userPostsTarget.userName}
          currentUserId={userId}
          isLoggedIn={isLoggedIn}
          onRequireLogin={onRequireLogin}
          onClose={() => setUserPostsTarget(null)}
        />
      )}
    </ModalFrame>
  )
}

function fmt(s: string) {
  try { return new Date(s).toLocaleString() } catch { return s }
}
