import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api, { errorMessage } from '../api/client'
import { useAuth } from '../context/authContext'

export default function Dashboard() {
  const { user } = useAuth()
  const [farms, setFarms] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [formError, setFormError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [saving, setSaving] = useState(false)
  const [version, setVersion] = useState(0)
  const [form, setForm] = useState({ name: '', location: '' })

  useEffect(() => {
    api
      .get('/api/farms')
      .then((res) => {
        setFarms(res.data)
        setError('')
      })
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false))
  }, [version])

  const reload = () => setVersion((v) => v + 1)

  const addFarm = async (e) => {
    e.preventDefault()
    setFormError('')
    if (form.name.trim().length < 2) return setFormError('Farm name is too short')
    if (form.location.trim().length < 2) return setFormError('Please enter a location')

    setSaving(true)
    try {
      await api.post('/api/farms', {
        name: form.name.trim(),
        location: form.location.trim(),
      })
      setForm({ name: '', location: '' })
      setShowForm(false)
      reload()
    } catch (err) {
      setFormError(errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  const deleteFarm = async (farm) => {
    if (!window.confirm(`Delete "${farm.name}" and all its fields and data?`)) return
    try {
      await api.delete(`/api/farms/${farm.id}`)
      reload()
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  const input =
    'w-full rounded border border-gray-300 px-3 py-2 focus:border-green-600 focus:outline-none'

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">
            Welcome, {user.full_name} 👋
          </h1>
          <p className="text-sm text-gray-500">Manage your farms and fields.</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="rounded bg-green-700 px-4 py-2 text-sm font-medium text-white hover:bg-green-800"
        >
          {showForm ? 'Cancel' : '+ Add farm'}
        </button>
      </div>

      {error && (
        <div className="rounded bg-red-50 p-3 text-sm text-red-700">{error}</div>
      )}

      {showForm && (
        <form onSubmit={addFarm} className="space-y-3 rounded-xl bg-white p-5 shadow">
          <h2 className="font-semibold text-gray-700">New farm</h2>
          {formError && (
            <div className="rounded bg-red-50 p-3 text-sm text-red-700">{formError}</div>
          )}
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium">Farm name</label>
              <input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className={input}
                placeholder="e.g. Mali Farm"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">Location</label>
              <input
                value={form.location}
                onChange={(e) => setForm({ ...form, location: e.target.value })}
                className={input}
                placeholder="e.g. Pune, Maharashtra"
              />
            </div>
          </div>
          <button
            type="submit"
            disabled={saving}
            className="rounded bg-green-700 px-4 py-2 text-sm font-medium text-white hover:bg-green-800 disabled:opacity-60"
          >
            {saving ? 'Saving...' : 'Save farm'}
          </button>
        </form>
      )}

      <div className="rounded-xl bg-white p-5 shadow">
        <h2 className="mb-3 font-semibold text-gray-700">
          Your farms {loading ? '' : `(${farms.length})`}
        </h2>

        {loading && <p className="text-gray-500">Loading...</p>}

        {!loading && farms.length === 0 && (
          <p className="text-gray-500">
            No farms yet. Click "+ Add farm" to create your first one.
          </p>
        )}

        <ul className="divide-y">
          {farms.map((farm) => (
            <li key={farm.id} className="flex items-center justify-between py-3">
              <Link to={`/farms/${farm.id}`} className="flex-1">
                <p className="font-medium text-green-800 hover:underline">{farm.name}</p>
                <p className="text-sm text-gray-500">{farm.location}</p>
              </Link>
              <button
                onClick={() => deleteFarm(farm)}
                className="rounded px-3 py-1 text-sm text-red-600 hover:bg-red-50"
              >
                Delete
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}