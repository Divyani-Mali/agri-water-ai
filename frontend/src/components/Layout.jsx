import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet } from 'react-router-dom'
import api from '../api/client'
import { useAuth } from '../context/authContext'

const linkClass = ({ isActive }) =>
  `rounded px-3 py-1 text-sm ${isActive ? 'bg-white/25' : 'hover:bg-white/15'}`

export default function Layout() {
  const { user, logout } = useAuth()
  const [unread, setUnread] = useState(0)

  // unread alert badge: refresh every 15 seconds and whenever the Alerts page changes something
  useEffect(() => {
    let active = true
    const load = () =>
      api
        .get('/api/alerts/unread-count')
        .then((res) => {
          if (active) setUnread(res.data.count)
        })
        .catch(() => {})
    load()
    const timer = setInterval(load, 15000)
    window.addEventListener('alerts-changed', load)
    return () => {
      active = false
      clearInterval(timer)
      window.removeEventListener('alerts-changed', load)
    }
  }, [])

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-green-700 text-white shadow">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-4 py-3">
          <div className="flex items-center gap-4">
            <Link to="/" className="text-lg font-bold">
              💧 Smart Irrigation AI
            </Link>
            <nav className="flex items-center gap-1">
              <NavLink to="/" end className={linkClass}>
                Farms
              </NavLink>
              <NavLink to="/alerts" className={linkClass}>
                Alerts
                {unread > 0 && (
                  <span className="ml-1 rounded-full bg-red-500 px-1.5 py-0.5 text-xs font-bold">
                    {unread > 99 ? '99+' : unread}
                  </span>
                )}
              </NavLink>
              {user.role === 'admin' && (
                <NavLink to="/admin" className={linkClass}>
                  Admin
                </NavLink>
              )}
            </nav>
          </div>
          <div className="flex items-center gap-4 text-sm">
            <span>{user.full_name}</span>
            <span className="rounded-full bg-green-900 px-2 py-0.5 text-xs uppercase">
              {user.role}
            </span>
            <button
              onClick={logout}
              className="rounded bg-white/20 px-3 py-1 hover:bg-white/30"
            >
              Logout
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}