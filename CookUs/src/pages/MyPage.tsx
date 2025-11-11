import { useEffect, useState } from 'react'
import { authAPI } from '../api/auth'
import type { User } from '../api/auth'
import EditProfileDialog from '../components/EditProfileDialog'
import BadgeGallery from '../components/badges/BadgeGallery'
import BadgeDisplaySelector from '../components/badges/BadgeDisplaySelector'
import { badgesAPI, type BadgeOverview } from '../api/badges'
import './MyPage.css'

type Props = { isLoggedIn: boolean; onRequireLogin: () => void }

export default function MyPage({ isLoggedIn, onRequireLogin }: Props) {
  const [me, setMe] = useState<User | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showEdit, setShowEdit] = useState(false)
  const [showDelete, setShowDelete] = useState(false)
  const [activeTab, setActiveTab] = useState<'profile' | 'badges'>('profile')
  const [badgeOverview, setBadgeOverview] = useState<BadgeOverview | null>(null)
  const [badgeLoading, setBadgeLoading] = useState(false)
  const [badgeError, setBadgeError] = useState<string | null>(null)
  const [showBadgeSelector, setShowBadgeSelector] = useState(false)
  const [displayLoading, setDisplayLoading] = useState(false)
  const [displayError, setDisplayError] = useState<string | null>(null)

  const fetchMe = async () => {
    setLoading(true); setError(null)
    try { setMe(await authAPI.me()) }
    catch { setError('내 정보를 불러오지 못했습니다.') }
    finally { setLoading(false) }
  }

  function FieldRow({
    label,
    value,
    chip,
    chipVariant = 'beige',
  }: {
    label: string
    value?: React.ReactNode
    chip?: string
    chipVariant?: 'beige' | 'mint'
  }) {
    return (
      <div className="field">
        <div className="field-label">{label}</div>
        <div className="field-val">
          {value && <div className="value">{value}</div>}
          {chip && (
            <span
              className={[
                'chip','chip--tiny',
                chipVariant === 'mint' ? 'ghost' : ''
              ].join(' ')}
            >
              {chip}
            </span>
          )}
        </div>
      </div>
    )
  }

  const fetchBadges = async () => {
    setBadgeError(null)
    try {
      setBadgeLoading(true)
      setBadgeOverview(await badgesAPI.overview())
    } catch {
      setBadgeOverview(null)
      setBadgeError('뱃지를 불러오지 못했어요.')
    } finally {
      setBadgeLoading(false)
    }
  }

  const displayedBadgeId =
    badgeOverview?.earned?.find(b => b.is_displayed)?.badge_id ?? null
  const earnedBadges = badgeOverview?.earned ?? []

  const handleBadgeDisplayChange = async (badgeId: number | null) => {
    if (displayLoading) return false
    setDisplayError(null)
    try {
      setDisplayLoading(true)
      await badgesAPI.setDisplayBadge(badgeId)
      await fetchBadges()
      return true
    } catch {
      setDisplayError('프로필에 표시할 뱃지를 바꾸지 못했어요.')
      return false
    } finally {
      setDisplayLoading(false)
    }
  }


  useEffect(() => {
    if (isLoggedIn) {
      fetchMe()
      fetchBadges()
    } else {
      setMe(null)
      setBadgeOverview(null)
      setBadgeError(null)
      setBadgeLoading(false)
    }
  }, [isLoggedIn])

  if (!isLoggedIn) {
    return (
      <section className="app-tab mypage">
        <div className="card my-card center">
          <h2 className="title">마이페이지</h2>
          <p className="sub">로그인이 필요합니다.</p>
          <button className="btn primary" onClick={onRequireLogin}>로그인</button>
        </div>
      </section>
    )
  }

  return (
    <section className="app-tab mypage">
      <div className="subtabs">
        <button
          type="button"
          className={["subtab-btn", activeTab === 'profile' ? 'active' : ''].join(' ')}
          onClick={() => setActiveTab('profile')}
        >
          프로필
        </button>
        <button
          type="button"
          className={["subtab-btn", activeTab === 'badges' ? 'active' : ''].join(' ')}
          onClick={() => setActiveTab('badges')}
        >
          뱃지 보기
        </button>
      </div>

      {activeTab === 'profile' && (
      <div className="card my-card">
        <div className="row">
          <div className="avatar">{(me?.user_name ?? 'U').slice(0,1)}</div>
          <div className="info">
            <div className="name">{me?.user_name ?? '—'}</div>
            <div className="uid">ID: {me?.user_id ?? '—'}</div>
          </div>
        </div>

        {loading && <div className="note">불러오는 중…</div>}
        {error && <div className="error">{error}</div>}

        <div className="divider" />

        <div className="fields">
          <FieldRow
            label="이메일"
            value={<span className="value-strong">{me?.email ?? '—'}</span>}
          />
          <FieldRow
            label="성별"
            chip={me?.gender ? (me.gender === 'male' ? '남' : '여') : undefined}
            chipVariant="mint"
          />
          <FieldRow label="생년월일" value={me?.date_of_birth ?? '—'} />
          <FieldRow label="주간 목표" value={me?.goal != null ? String(me.goal) : '—'} />
          <FieldRow
            label="요리 레벨"
            chip={me?.cooking_level ?? undefined}
            chipVariant="beige"
          />
        </div>

        <div className="actions">
          <button className="editbtn" onClick={() => setShowEdit(true)}>프로필 수정</button>
        </div>
        <div style={{display:'flex', justifyContent:'flex-end', marginTop:8}}>
          <a role="link" onClick={()=>setShowDelete(true)} style={{cursor:'pointer', fontSize:12, color:'#9ca3af', textDecoration:'none'}}>회원탈퇴</a>
        </div>
      </div>
      )}

      {activeTab === 'badges' && (
        <div className="card my-card">
          <div className="my-badge-header">
            <h3 style={{marginTop:0}}>나의 뱃지</h3>
            <button
              type="button"
              className="btn btn--tiny"
              onClick={() => { setDisplayError(null); setShowBadgeSelector(true) }}
              disabled={earnedBadges.length === 0}
            >
              프로필 표시 선택
            </button>
          </div>
          {badgeLoading && <div className="note">뱃지를 불러오는 중...</div>}
          {badgeError && <div className="error">{badgeError}</div>}
          {!badgeLoading && !badgeError && !badgeOverview && (
            <div className="note">아직 획득한 배지가 없어요.</div>
          )}
          {badgeOverview && (
            <BadgeGallery
              overview={badgeOverview}
              displayedBadgeId={displayedBadgeId}
              onDisplayChange={handleBadgeDisplayChange}
              displayLoading={displayLoading}
              displayError={displayError}
            />
          )}
        </div>
      )}
      {showEdit && me && (
        <EditProfileDialog
          me={me}
          onClose={() => setShowEdit(false)}
          onSaved={async () => { setShowEdit(false); await fetchMe() }}
        />
      )}
      {showDelete && (
        <DeleteAccountDialog onClose={()=>setShowDelete(false)} />
      )}
      {showBadgeSelector && badgeOverview && (
        <BadgeDisplaySelector
          earnedBadges={badgeOverview.earned}
          displayedBadgeId={displayedBadgeId}
          onSelect={handleBadgeDisplayChange}
          loading={displayLoading}
          error={displayError}
          onClose={() => setShowBadgeSelector(false)}
        />
      )}
    </section>
  )
}

function DeleteAccountDialog({ onClose }: { onClose: () => void }){
  const [pw, setPw] = useState('')
  const [pw2, setPw2] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [done, setDone] = useState(false)
  const [confirmOpen, setConfirmOpen] = useState(false)

  const submit = async () => {
    setErr(null)
    if (!pw || !pw2) { setErr('비밀번호를 입력해 주세요.'); return }
    if (pw !== pw2) { setErr('비밀번호가 일치하지 않습니다.'); return }
    // 1차 확인 모달 열기 (별도 모달)
    setConfirmOpen(true)
  }

  const doDelete = async () => {
    setErr(null)
    try{
      setBusy(true)
      await authAPI.deleteMe(pw, pw2)
      setDone(true)
      // 잠깐 감사 카드 보여준 뒤 메인으로 이동
      window.setTimeout(() => {
        window.location.href = '/'
      }, 1500)
    } catch(e:any){
      setErr(e?.response?.data?.detail ?? '탈퇴에 실패했습니다.')
    } finally { setBusy(false) }
  }

  if (done) {
    return (
      <div className="inner-overlay" onClick={onClose}>
        <div className="modal card rec-modal" onClick={e=>e.stopPropagation()} style={{maxWidth:360, textAlign:'center'}}>
          <h3 style={{margin:'10px 0'}}>그동안 이용해주셔서 감사합니다.</h3>
          <div className="muted">계정이 삭제 처리되었습니다.</div>
        </div>
      </div>
    )
  }

  return (
    <div className="inner-overlay" onClick={onClose}>
      <div className="modal card rec-modal" onClick={e=>e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>×</button>
        <h3 style={{marginTop:0}}>회원 탈퇴</h3>
        <p className="muted">계정 정보가 비식별화되고 로그인할 수 없게 됩니다.</p>
        <div style={{display:'grid', gap:8, marginTop:10}}>
          <input type="password" placeholder="비밀번호" value={pw} onChange={e=>setPw(e.target.value)} style={{padding:'10px 12px', border:'1px solid #e5e7eb', borderRadius:10}} />
          <input type="password" placeholder="비밀번호 확인" value={pw2} onChange={e=>setPw2(e.target.value)} style={{padding:'10px 12px', border:'1px solid #e5e7eb', borderRadius:10}} />
        </div>
        {err && <div className="error" style={{marginTop:8}}>{err}</div>}
        <div style={{display:'flex', justifyContent:'flex-end', gap:8, marginTop:12}}>
          <button className="btn" onClick={onClose} disabled={busy}>취소</button>
          <button className="btn danger" onClick={submit} disabled={busy}>탈퇴</button>
        </div>
      </div>
      {confirmOpen && (
        <div className="inner-overlay" onClick={()=>setConfirmOpen(false)}>
          <div className="modal card rec-modal" onClick={e=>e.stopPropagation()} style={{maxWidth:360}}>
            <button className="modal-close" onClick={()=>setConfirmOpen(false)}>×</button>
            <h3 style={{marginTop:0}}>정말 탈퇴하시겠습니까?</h3>
            <p className="muted">탈퇴 이후에는 되돌릴 수 없습니다.</p>
            <div style={{display:'flex', justifyContent:'flex-end', gap:8}}>
              <button className="btn" onClick={()=>setConfirmOpen(false)} disabled={busy}>취소</button>
              <button className="btn danger" onClick={doDelete} disabled={busy}>확인</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
