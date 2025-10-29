import { useEffect, useState } from 'react'
import { authAPI } from '../api/auth'
import type { User } from '../api/auth'
import EditProfileDialog from '../components/EditProfileDialog'
import './MyPage.css'

type Props = { isLoggedIn: boolean; onRequireLogin: () => void }

export default function MyPage({ isLoggedIn, onRequireLogin }: Props) {
  const [me, setMe] = useState<User | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showEdit, setShowEdit] = useState(false)

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


  useEffect(() => {
    if (isLoggedIn) fetchMe()
    else setMe(null)
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
          <button className="btn" onClick={() => setShowEdit(true)}>프로필 수정</button>
        </div>
      </div>

      {showEdit && me && (
        <EditProfileDialog
          me={me}
          onClose={() => setShowEdit(false)}
          onSaved={async () => { setShowEdit(false); await fetchMe() }}
        />
      )}
    </section>
  )
}