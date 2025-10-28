// src/App.tsx
import { useEffect, useState } from 'react'
import './App.css'

import Fridge from './pages/Fridge'
import Calendar from './pages/Calendar'
import Dashboard from './pages/Dashboard'
import MyPage from './pages/MyPage'
import Navigation from './components/Navigation'
import LoginModal from './components/LoginModal'

import { authAPI } from './api/auth'

export type User = { user_id: string; user_name: string }
export type TabKey = 'fridge' | 'calendar' | 'dashboard' | 'mypage'

export default function App() {
  const [tab, setTab] = useState<TabKey>('fridge')
  const [user, setUser] = useState<User | null>(null)
  const [showLogin, setShowLogin] = useState(false)
  const [booting, setBooting] = useState(true)

  useEffect(() => {
    (async () => {
      const ok = await authAPI.init()
      if (ok) {
        try { setUser(await authAPI.me()) }
        catch { /* ignore */ }
      }
      setBooting(false)
    })()
  }, [])

  const isLoggedIn = !!user
  const requireLogin = () => setShowLogin(true)

  const handleLoginSuccess = (u: User) => {
    setUser(u)
    setShowLogin(false)
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
          onLogout={handleLogout}
        />

        <main className="app-main">
          {tab === 'fridge' && (
            <Fridge isLoggedIn={isLoggedIn} onRequireLogin={requireLogin} />
          )}

          {tab === 'calendar' && (
            <Calendar isLoggedIn={isLoggedIn} />
          )}

          {tab === 'dashboard' && (
            <Dashboard />
          )}

          {tab === 'mypage' && (
            <MyPage isLoggedIn={isLoggedIn} onRequireLogin={requireLogin} />
          )}
        </main>
      </div>

      {showLogin && (
        <LoginModal onClose={() => setShowLogin(false)} onSuccess={handleLoginSuccess} />
      )}
    </div>
  )
}
