import './Navigation.css'
import type { TabKey, User } from '../App'
import { BadgeIcon } from './badges/BadgeSet'
import { badgeMetaById } from '../data/badges'

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
  current,
  onChange,
  isLoggedIn,
  user,
  onLoginClick,
  onSignupClick,
  onLogout,
}: Props) {
  const tabLabel = (key: TabKey) => {
    switch (key) {
      case 'fridge': return '냉장고'
      case 'calendar': return '캘린더'
      case 'dashboard': return '대시보드'
      case 'cooktest': return '쿡테스트'
      case 'nutrition': return '영양관리'
      case 'mypage': return '마이페이지'
      default: return key
    }
  }

  const displayedBadgeId = user?.displayed_badge_id ?? null
  const displayedBadgeMeta = displayedBadgeId ? badgeMetaById[displayedBadgeId] : undefined
  const displayedBadgeCode = displayedBadgeMeta?.iconCode

  const renderTabContent = (key: TabKey) => {
    if (key === 'fridge') {
      return (
        <>
          <span className="tab-icon tab-icon--fridge" aria-hidden>
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <rect x="6" y="3" width="12" height="18" rx="2" />
              <line x1="6" y1="11" x2="18" y2="11" />
              <line x1="9" y1="7" x2="9" y2="10" />
              <line x1="15" y1="14" x2="15" y2="17" />
            </svg>
          </span>
          <span className="sr-only">{tabLabel(key)}</span>
        </>
      )
    }

    if (key === 'calendar') {
      return (
        <>
          <span className="tab-icon tab-icon--calendar" aria-hidden>
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <rect x="3" y="4" width="18" height="17" rx="3" />
              <line x1="8" y1="2.5" x2="8" y2="6" />
              <line x1="16" y1="2.5" x2="16" y2="6" />
              <line x1="3" y1="10" x2="21" y2="10" />
              <circle cx="8.5" cy="14.5" r="1" />
              <circle cx="12" cy="14.5" r="1" />
              <circle cx="15.5" cy="14.5" r="1" />
            </svg>
          </span>
          <span className="sr-only">{tabLabel(key)}</span>
        </>
      )
    }

    if (key === 'dashboard') {
      return (
        <>
          <span className="tab-icon tab-icon--dashboard" aria-hidden>
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <rect x="5" y="11" width="3.2" height="9" rx="1" />
              <rect x="10.4" y="6" width="3.2" height="14" rx="1" />
              <rect x="15.8" y="14" width="3.2" height="6" rx="1" />
              <path d="M4 20h16" />
            </svg>
          </span>
          <span className="sr-only">{tabLabel(key)}</span>
        </>
      )
    }

    if (key === 'cooktest') {
      return (
        <>
          <span className="tab-icon tab-icon--cooktest" aria-hidden>
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M8 5V3h8v2" />
              <path d="M6 5h12v4a4 4 0 0 1-4 4h-4a4 4 0 0 1-4-4V5Z" />
              <path d="M6 5H4v2a3 3 0 0 0 3 3" />
              <path d="M18 5h2v2a3 3 0 0 1-3 3" />
              <path d="M9 15h6v2a3 3 0 0 1-3 3 3 3 0 0 1-3-3v-2Z" />
            </svg>
          </span>
          <span className="sr-only">{tabLabel(key)}</span>
        </>
      )
    }

    if (key === 'nutrition') {
      return (
        <>
          <span className="tab-icon tab-icon--nutrition" aria-hidden>
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 3.5c-2.9 0-5 2.1-5 5v7c0 2.9 2.1 5 5 5s5-2.1 5-5v-7c0-2.9-2.1-5-5-5Z" />
              <path d="M7 12h10" />
              <path d="M9 6.5h6" />
            </svg>
          </span>
          <span className="sr-only">{tabLabel(key)}</span>
        </>
      )
    }

    if (key === 'mypage') {
      return (
        <>
          <span className="tab-icon" aria-hidden title="마이페이지">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
          </span>
          <span className="sr-only">{tabLabel(key)}</span>
        </>
      )
    }

    return tabLabel(key)
  }

  return (
    <header className="app-header">
      {/* top bar */}
      <div className="topbar">
        <div /> {/* left spacer */}
        <div className="brand-center only-text">
          <span className="brand-text">COOKUS</span>
          {displayedBadgeCode && (
            <span className="brand-badge" aria-hidden>
              <BadgeIcon code={displayedBadgeCode} earned size={28} />
            </span>
          )}
        </div>
        <div className="user-area">
          {!isLoggedIn ? (
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn ghost" onClick={onLoginClick}>로그인</button>
              {onSignupClick && (
                <button className="btn" onClick={onSignupClick}>회원가입</button>
              )}
            </div>
          ) : (
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <span>{user?.user_name ?? '사용자'}님</span>
              <button className="btn ghost" onClick={onLogout}>로그아웃</button>
            </div>
          )}
        </div>
      </div>

      <div className="tab-sep-line" />
      <nav className="tabbar">
        {(['fridge', 'calendar', 'dashboard', 'cooktest', 'nutrition', 'mypage'] as TabKey[]).map((t) => (
          <button
            key={t}
            className={`tab ${current === t ? 'active' : ''}`}
            onClick={() => onChange(t)}
          >
            {renderTabContent(t)}
          </button>
        ))}
      </nav>
    </header>
  )
}
