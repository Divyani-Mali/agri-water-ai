import { useCallback, useEffect, useState } from 'react'
import api, { errorMessage } from '../api/client'
import { useAuth } from '../context/authContext'
import { fmtTime } from '../constants'

function Stat({ title, value }) {
  return (
    <div className="rounded-xl bg-white p-4 shadow">
      <p className="text-xs uppercase tracking-wide text-gray-400">{title}</p>
      <p className="mt-1 text-2xl font-bold text-gray-800">{value}</p>
    </div>
  )
}

export default function Admin() {
  const { user: me } = useAuth()
  const [stats, setStats] = useState(null)
  const [users, setUsers] = useState([])
  const [error, setError] = useState('')

  const load = useCallback(() => {
    Promise.all([api.get('/api/admin/stats'), api.get('/api/admin/users')])
      .then(([s, u]) => {
        setStats(s.data)
        setUsers(u.data)
        setError('')
      })
      .catch((err) => setError(errorMessage(err)))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const update = async (u, body, question) => {
    if (!window.confirm(question)) return
    try {
      await api.patch(`/api/admin/users/${u.id}`, body)
      load()
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-800">Admin panel</h1>
        <p className="text-sm text-gray-500">System overview and user management.</p>
      </div>

      {error && (
        <div className="rounded bg-red-50 p-3 text-sm text-red-700">{error}</div>
      )}

      {stats && (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
          <Stat title="Users" value={stats.users} />
          <Stat title="Farms" value={stats.farms} />
          <Stat title="Fields" value={stats.fields} />
          <Stat title="Sensor readings" value={stats.readings.toLocaleString('en-IN')} />
          <Stat title="Unread alerts" value={stats.unread_alerts} />
        </div>
      )}

      <div className="overflow-x-auto rounded-xl bg-white p-5 shadow">
        <h2 className="mb-3 font-semibold text-gray-700">Users ({users.length})</h2>
        <table className="w-full text-left text-sm">
          <thead className="border-b text-xs uppercase text-gray-400">
            <tr>
              <th className="py-2">Name</th>
              <th>Email</th>
              <th>Role</th>
              <th>Status</th>
              <th>Joined</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {users.map((u) => {
              const isMe = u.id === me.id
              return (
                <tr key={u.id}>
                  <td className="py-2 font-medium">
                    {u.full_name} {isMe && <span className="text-xs text-gray-400">(you)</span>}
                  </td>
                  <td>{u.email}</td>
                  <td className="capitalize">{u.role}</td>
                  <td>
                    <span className={u.is_active ? 'text-green-600' : 'text-red-600'}>
                      {u.is_active ? 'Active' : 'Disabled'}
                    </span>
                  </td>
                  <td>{fmtTime(u.created_at)}</td>
                  <td className="space-x-2 whitespace-nowrap">
                    <button
                      disabled={isMe}
                      onClick={() =>
                        update(
                          u,
                          { is_active: !u.is_active },
                          `${u.is_active ? 'Disable' : 'Enable'} ${u.full_name}?`
                        )
                      }
                      className="rounded border px-2 py-1 text-xs hover:bg-gray-50 disabled:opacity-40"
                    >
                      {u.is_active ? 'Disable' : 'Enable'}
                    </button>
                    <button
                      disabled={isMe}
                      onClick={() =>
                        update(
                          u,
                          { role: u.role === 'admin' ? 'farmer' : 'admin' },
                          `Make ${u.full_name} ${u.role === 'admin' ? 'a farmer' : 'an admin'}?`
                        )
                      }
                      className="rounded border px-2 py-1 text-xs hover:bg-gray-50 disabled:opacity-40"
                    >
                      Make {u.role === 'admin' ? 'farmer' : 'admin'}
                    </button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}