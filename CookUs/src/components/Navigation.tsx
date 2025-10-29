import './Navigation.css'
import type { TabKey, User } from '../App'

type Props = {
  current: TabKey
  onChange: (t: TabKey) => void
  isLoggedIn: boolean
  user: User | null
  onLoginClick: () => void
  onSignupClick?: () => void
  onLogout: () => void
}

export default function Navigation({
  current, onChange, isLoggedIn, user, onLoginClick, onSignupClick, onLogout,
}: Props) {
  return (
    <header className="app-header">
      {/* 상단 바: 중앙 브랜드 텍스트, 우측 사용자 */}
      <div className="topbar">
        <div /> {/* left spacer */}
        <div className="brand-center only-text">
          <span className="brand-text">COOKUS</span>
        </div>
        <div className="user-area">
          {!isLoggedIn ? (
            <div style={{ display:'flex', gap:8 }}>
              <button className="btn ghost" onClick={onLoginClick}>로그인</button>
              {onSignupClick && (
                <button className="btn" onClick={onSignupClick}>회원가입</button>
              )}
            </div>
          ) : (
            <div style={{ display:'flex', gap:8, alignItems:'center' }}>
              <span>{user?.user_name}님</span>
              <button className="btn ghost" onClick={onLogout}>로그아웃</button>
            </div>
          )}
        </div>
      </div>

      {/* 탭 위 가로선 + 탭 */}
      <div className="tab-sep-line" />
      <nav className="tabbar">
        {(['fridge','calendar','dashboard','mypage'] as TabKey[]).map(t => (
          <button
            key={t}
            className={`tab ${current === t ? 'active' : ''}`}
            onClick={() => onChange(t)}
          >
            {t === 'fridge' ? '냉장고' :
             t === 'calendar' ? '캘린더' :
             t === 'dashboard' ? '대시보드' : '마이페이지'}
          </button>
        ))}
      </nav>
    </header>
  )
}
