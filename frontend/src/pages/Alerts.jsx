import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api, { errorMessage } from '../api/client'
import { fmtTime } from '../constants'

const STYLE = {
  critical: { box: 'border-red-300 bg-red-50', badge: 'bg-red-600', icon: '🚨' },
  warning: { box: 'border-amber-300 bg-amber-50', badge: 'bg-amber-500', icon: '⚠️' },
  info: { box: 'border-blue-200 bg-blue-50', badge: 'bg-blue-500', icon: 'ℹ️' },
}

const notifyNavbar = () => window.dispatchEvent(new Event('alerts-changed'))

export default function Alerts() {
  const [alerts, setAlerts] = useState([])
  const [unreadOnly, setUnreadOnly] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(() => {
    api
      .get('/api/alerts', { params: { unread_only: unreadOnly, limit: 100 } })
      .then((res) => {
        setAlerts(res.data)
        setError('')
      })
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false))
  }, [unreadOnly])

  useEffect(() => {
    load()
    const timer = setInterval(load, 10000)
    return () => clearInterval(timer)
  }, [load])

  const markRead = async (id) => {
    try {
      await api.post(`/api/alerts/${id}/read`)
      load()
      notifyNavbar()
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  const markAll = async () => {
    try {
      await api.post('/api/alerts/read-all')
      load()
      notifyNavbar()
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  const unreadCount = alerts.filter((a) => !a.is_read).length

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Alerts</h1>
          <p className="text-sm text-gray-500">
            Automatic warnings from your sensors. Updates every 10 seconds.
          </p>
        </div>
        <div className="flex items-center gap-3 text-sm">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={unreadOnly}
              onChange={(e) => {
                setLoading(true)
                setUnreadOnly(e.target.checked)
              }}
            />
            Unread only
          </label>
          <button
            onClick={markAll}
            disabled={unreadCount === 0}
            className="rounded bg-green-700 px-3 py-1.5 text-white hover:bg-green-800 disabled:opacity-40"
          >
            Mark all as read
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded bg-red-50 p-3 text-sm text-red-700">{error}</div>
      )}

      {loading && <p className="text-gray-500">Loading...</p>}

      {!loading && alerts.length === 0 && (
        <div className="rounded-xl bg-white p-8 text-center text-gray-500 shadow">
          ✅ No alerts. Everything looks fine.
        </div>
      )}

      <div className="space-y-3">
        {alerts.map((a) => {
          const s = STYLE[a.severity] || STYLE.info
          return (
            <div
              key={a.id}
              className={`rounded-xl border p-4 ${s.box} ${a.is_read ? 'opacity-60' : ''}`}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span>{s.icon}</span>
                    <span
                      className={`rounded px-2 py-0.5 text-xs font-semibold uppercase text-white ${s.badge}`}
                    >
                      {a.severity}
                    </span>
                    <span className="text-xs text-gray-500">{fmtTime(a.created_at)}</span>
                  </div>
                  <p className="mt-2 text-gray-800">{a.message}</p>
                  <Link
                    to={`/fields/${a.field_id}`}
                    className="mt-1 inline-block text-sm text-green-700 hover:underline"
                  >
                    Open {a.field_name} →
                  </Link>
                </div>
                {!a.is_read && (
                  <button
                    onClick={() => markRead(a.id)}
                    className="shrink-0 rounded border border-gray-300 bg-white px-3 py-1 text-xs hover:bg-gray-50"
                  >
                    Mark read
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}