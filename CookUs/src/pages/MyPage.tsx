import { useEffect, useState } from 'react'
import { authAPI } from '../api/auth'
import type { User } from '../App'
import './MyPage.css'

type Props = { isLoggedIn: boolean; onRequireLogin: () => void }

export default function MyPage({ isLoggedIn, onRequireLogin }: Props) {
  const [me, setMe] = useState<User | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    const run = async () => {
      if (!isLoggedIn) { setMe(null); return }
      setLoading(true); setError(null)
      try {
        const data = await authAPI.me()
        if (alive) setMe(data)
      } catch (e) {
        if (alive) setError('내 정보를 불러오지 못했습니다.')
      } finally {
        if (alive) setLoading(false)
      }
    }
    run()
    return () => { alive = false }
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

        <div className="grid">
          <Item label="목표(주)" value="—" />
          <Item label="요리 레벨" value="—" />
          <Item label="이메일" value="—" />
        </div>

        <div className="actions">
          <button className="btn ghost" onClick={onRequireLogin}>프로필 수정(준비중)</button>
        </div>
        <p className="hint">※ 현재 백엔드 /me 응답은 user_id, user_name만 제공 중이에요.</p>
      </div>
    </section>
  )
}

function Item({label, value}:{label:string; value:string}) {
  return (
    <div className="item">
      <div className="label">{label}</div>
      <div className="value">{value}</div>
    </div>
  )
}
