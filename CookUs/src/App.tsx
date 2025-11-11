// src/App.tsx
import { useCallback, useEffect, useState } from 'react'
import './App.css'

import Fridge from './pages/Fridge'
import Calendar from './pages/Calendar'
import Dashboard from './pages/Dashboard'
import MyPage from './pages/MyPage'
import Navigation from './components/Navigation'
import LoginDialog from './components/LoginDialog'
import SignupDialog from './components/SignupDialog'

import { authAPI } from './api/auth'
import CookTest from './pages/CookTest'
import Nutrition from './pages/Nutrition'
import Notifications from './components/Notifications'

export type User = { user_id: string; user_name: string; displayed_badge_id?: number | null }
export type TabKey = 'fridge' | 'calendar' | 'dashboard' | 'cooktest' | 'nutrition' | 'mypage'

export default function App() {
  const [tab, setTab] = useState<TabKey>('fridge')
  const [user, setUser] = useState<User | null>(null)
  const [showLogin, setShowLogin] = useState(false)
  const [booting, setBooting] = useState(true)
  const [showSignup, setShowSignup] = useState(false)

  const refreshUser = useCallback(async () => {
    try {
      const profile = await authAPI.me()
      setUser(profile)
      return profile
    } catch (err) {
      setUser(null)
      throw err
    }
  }, [])

  useEffect(() => {
    (async () => {
      const ok = await authAPI.init()
      if (ok) {
        try {
          await refreshUser()
        } catch {
          /* ignore */
        }
      }
      setBooting(false)
    })()
  }, [refreshUser])

  const isLoggedIn = !!user
  const requireLogin = () => setShowLogin(true)

  const handleLoginSuccess = async (_u: User) => {
    try {
      await refreshUser()
    } finally {
      setShowLogin(false)
    }
  }

  const handleLogout = async () => {
    try { await authAPI.logout() } catch {}
    setUser(null)
    setTab('fridge')
  }

  if (booting) {
    return <div className="app-shell"><div className="app-frame"><main className="app-main">로딩 중…</main></div></div>
  }

  return (
    <div className="app-shell">
      <div className="app-frame">
        <Navigation
          current={tab}
          onChange={setTab}
          isLoggedIn={isLoggedIn}
          user={user}
          onLoginClick={() => setShowLogin(true)}
          onSignupClick={() => setShowSignup(true)}
          onLogout={handleLogout}
        />

        {/* ✅ 알림 벨/드롭다운 (로그인 시에만). 절대 위치로 좌상단 고정 */}
        {isLoggedIn && (<Notifications isLoggedIn={isLoggedIn} />)}

        <main className={`app-main ${tab === 'dashboard' ? 'app-main--dashboard' : ''}`}>
          {tab === 'fridge' && (
            <Fridge isLoggedIn={isLoggedIn} onRequireLogin={requireLogin} />
          )}

          {tab === 'calendar' && (
            <Calendar isLoggedIn={isLoggedIn} userName={user?.user_name} />
          )}

          {tab === 'cooktest' && (
            <CookTest
              isLoggedIn={isLoggedIn}
              onRequireLogin={requireLogin}
              userId={user?.user_id}
            />
          )}

          {tab === 'dashboard' && (
            <Dashboard isLoggedIn={isLoggedIn} onRequireLogin={requireLogin}/>
          )}

          {tab === 'nutrition' && (
            <Nutrition isLoggedIn={isLoggedIn} onRequireLogin={requireLogin} userName={user?.user_name} />
          )}

          {tab === 'mypage' && (
            <MyPage
              isLoggedIn={isLoggedIn}
              onRequireLogin={requireLogin}
              user={user}
              refreshUser={refreshUser}
            />
          )}
        </main>
      </div>

      {showLogin && (
        <LoginDialog onClose={() => setShowLogin(false)} onSuccess={handleLoginSuccess} />
      )}

      {showSignup && (
        <SignupDialog
          onClose={() => setShowSignup(false)}
          onSuccess={(u) => { setUser(u); setShowSignup(false); }}
        />
      )}
    </div>
  )
}
