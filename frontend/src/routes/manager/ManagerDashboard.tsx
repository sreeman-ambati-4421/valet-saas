import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../../auth/AuthContext'
import { Layout } from '../../components/Layout'
import { apiFetch, ApiError } from '../../lib/api'
import type { SessionState, ValetSession } from '../../lib/types'

const POLL_MS = 5000

const ALL_STATES: SessionState[] = [
  'REQUESTED',
  'ASSIGNED',
  'VEHICLE_COLLECTED',
  'PARKED',
  'RETRIEVAL_REQUESTED',
  'RETRIEVING',
  'READY',
  'DELIVERED',
  'COMPLETED',
  'CANCELLED',
]

export function ManagerDashboard() {
  const { session, me } = useAuth()
  const accessToken = session?.access_token ?? null
  const [venueId, setVenueId] = useState<string | null>(me?.venues[0]?.id ?? null)
  const [sessions, setSessions] = useState<ValetSession[]>([])
  const [stateFilter, setStateFilter] = useState<SessionState | ''>('')
  const [regFilter, setRegFilter] = useState('')
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!venueId || !accessToken) return
    const params = new URLSearchParams()
    if (stateFilter) params.set('state', stateFilter)
    if (regFilter) params.set('registration_number', regFilter)
    try {
      const data = await apiFetch<ValetSession[]>(
        `/venues/${venueId}/sessions?${params.toString()}`,
        accessToken
      )
      setSessions(data)
      setError(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to load sessions')
    }
  }, [venueId, accessToken, stateFilter, regFilter])

  useEffect(() => {
    void load()
    const interval = setInterval(() => void load(), POLL_MS)
    return () => clearInterval(interval)
  }, [load])

  if (!me) return null

  if (me.venues.length === 0) {
    return (
      <Layout title="Manager">
        <p className="text-gray-400">No venues assigned yet.</p>
      </Layout>
    )
  }

  return (
    <Layout title="Manager — Session Overview">
      <div className="mb-4 flex flex-wrap gap-3">
        {me.venues.length > 1 && (
          <select
            value={venueId ?? ''}
            onChange={(e) => setVenueId(e.target.value)}
            className="rounded-md border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm"
          >
            {me.venues.map((v) => (
              <option key={v.id} value={v.id}>
                {v.name}
              </option>
            ))}
          </select>
        )}
        <select
          value={stateFilter}
          onChange={(e) => setStateFilter(e.target.value as SessionState | '')}
          className="rounded-md border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm"
        >
          <option value="">All states</option>
          {ALL_STATES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <input
          placeholder="Search reg. number"
          value={regFilter}
          onChange={(e) => setRegFilter(e.target.value)}
          className="rounded-md border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm"
        />
      </div>

      {error && <p className="mb-4 rounded-md bg-red-950 px-3 py-2 text-sm text-red-300">{error}</p>}

      <div className="overflow-x-auto rounded-lg border border-gray-800">
        <table className="w-full text-left text-sm">
          <thead className="bg-gray-900 text-gray-400">
            <tr>
              <th className="px-4 py-2">Reg. Number</th>
              <th className="px-4 py-2">Guest Phone</th>
              <th className="px-4 py-2">State</th>
              <th className="px-4 py-2">Key Tag</th>
              <th className="px-4 py-2">Updated</th>
            </tr>
          </thead>
          <tbody>
            {sessions.map((s) => (
              <tr key={s.id} className="border-t border-gray-800">
                <td className="px-4 py-2 font-medium">{s.registration_number}</td>
                <td className="px-4 py-2 text-gray-400">{s.guest_phone_number}</td>
                <td className="px-4 py-2 uppercase tracking-wide text-gray-300">{s.state.replace('_', ' ')}</td>
                <td className="px-4 py-2 text-gray-400">{s.key_tag ?? '—'}</td>
                <td className="px-4 py-2 text-gray-500">{new Date(s.updated_at).toLocaleTimeString()}</td>
              </tr>
            ))}
            {sessions.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-gray-500">
                  No sessions match this filter.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </Layout>
  )
}
