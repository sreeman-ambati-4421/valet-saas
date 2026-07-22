import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { useAuth } from '../../auth/AuthContext'
import { Layout } from '../../components/Layout'
import { apiFetch, ApiError } from '../../lib/api'
import type { ValetSession } from '../../lib/types'

const POLL_MS = 4000

const NEXT_ACTION: Partial<Record<ValetSession['state'], { label: string; path: string }>> = {
  ACCEPTED: { label: 'Mark Parked', path: 'park' },
  PARKED: { label: 'Request Retrieval', path: 'request-retrieval' },
  RETRIEVAL_REQUESTED: { label: 'Mark Retrieving', path: 'retrieving' },
  RETRIEVING: { label: 'Mark Ready', path: 'ready' },
  READY: { label: 'Complete', path: 'complete' },
}

export function ValetDeskDashboard() {
  const { session, me } = useAuth()
  const accessToken = session?.access_token ?? null
  const [venueId, setVenueId] = useState<string | null>(me?.venues[0]?.id ?? null)
  const [sessions, setSessions] = useState<ValetSession[]>([])
  const [error, setError] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [newReg, setNewReg] = useState('')
  const [newPhone, setNewPhone] = useState('')
  const [newName, setNewName] = useState('')
  const [parkingSession, setParkingSession] = useState<ValetSession | null>(null)
  const [keyTag, setKeyTag] = useState('')

  const load = useCallback(async () => {
    if (!venueId || !accessToken) return
    try {
      const data = await apiFetch<ValetSession[]>(`/venues/${venueId}/sessions`, accessToken)
      setSessions(data)
      setError(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to load sessions')
    }
  }, [venueId, accessToken])

  useEffect(() => {
    void load()
    const interval = setInterval(() => void load(), POLL_MS)
    return () => clearInterval(interval)
  }, [load])

  if (!me) return null

  if (me.venues.length === 0) {
    return (
      <Layout title="Valet Desk">
        <p className="text-gray-400">You are not assigned to any venue yet. Ask your business owner to grant venue access.</p>
      </Layout>
    )
  }

  async function createSession(e: FormEvent) {
    e.preventDefault()
    if (!venueId || !accessToken) return
    try {
      await apiFetch(`/venues/${venueId}/sessions`, accessToken, {
        method: 'POST',
        body: JSON.stringify({
          registration_number: newReg,
          guest_phone_number: newPhone,
          guest_name: newName || null,
        }),
      })
      setNewReg('')
      setNewPhone('')
      setNewName('')
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to create session')
    }
  }

  async function runAction(s: ValetSession, path: string) {
    if (!accessToken) return
    setBusyId(s.id)
    try {
      await apiFetch(`/sessions/${s.id}/${path}`, accessToken, { method: 'POST' })
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Action failed')
    } finally {
      setBusyId(null)
    }
  }

  async function submitPark(e: FormEvent) {
    e.preventDefault()
    if (!accessToken || !parkingSession) return
    setBusyId(parkingSession.id)
    try {
      await apiFetch(`/sessions/${parkingSession.id}/park`, accessToken, {
        method: 'POST',
        body: JSON.stringify({ key_tag: keyTag, parking_zone_id: null, parking_slot_id: null }),
      })
      setParkingSession(null)
      setKeyTag('')
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to park vehicle')
    } finally {
      setBusyId(null)
    }
  }

  const active = sessions.filter((s) => !['COMPLETED', 'CANCELLED'].includes(s.state))
  const finished = sessions.filter((s) => s.state === 'COMPLETED')

  return (
    <Layout title="Valet Desk Queue">
      {me.venues.length > 1 && (
        <select
          value={venueId ?? ''}
          onChange={(e) => setVenueId(e.target.value)}
          className="mb-4 rounded-md border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm"
        >
          {me.venues.map((v) => (
            <option key={v.id} value={v.id}>
              {v.name}
            </option>
          ))}
        </select>
      )}

      {error && <p className="mb-4 rounded-md bg-red-950 px-3 py-2 text-sm text-red-300">{error}</p>}

      <form onSubmit={createSession} className="mb-6 grid grid-cols-1 gap-3 rounded-lg border border-gray-800 bg-gray-900 p-4 sm:grid-cols-4">
        <input
          required
          placeholder="Vehicle reg. number"
          value={newReg}
          onChange={(e) => setNewReg(e.target.value)}
          className="rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm"
        />
        <input
          required
          placeholder="Guest phone (+91...)"
          value={newPhone}
          onChange={(e) => setNewPhone(e.target.value)}
          className="rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm"
        />
        <input
          placeholder="Guest name (optional)"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          className="rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm"
        />
        <button type="submit" className="rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium hover:bg-indigo-500">
          New Request
        </button>
      </form>

      {parkingSession && (
        <form onSubmit={submitPark} className="mb-6 flex items-center gap-3 rounded-lg border border-amber-800 bg-amber-950/40 p-4">
          <span className="text-sm">Parking {parkingSession.registration_number} — key tag:</span>
          <input
            required
            autoFocus
            value={keyTag}
            onChange={(e) => setKeyTag(e.target.value)}
            className="rounded-md border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm"
          />
          <button type="submit" className="rounded-md bg-amber-600 px-3 py-1.5 text-sm font-medium hover:bg-amber-500">
            Confirm Parked
          </button>
          <button type="button" onClick={() => setParkingSession(null)} className="text-sm text-gray-400">
            Cancel
          </button>
        </form>
      )}

      <div className="space-y-2">
        {active.length === 0 && <p className="text-gray-500">No active sessions.</p>}
        {active.map((s) => {
          const isMine = s.accepted_by_user_id === me.id
          const isUnaccepted = s.state === 'REQUESTED' && !s.accepted_by_user_id
          const next = NEXT_ACTION[s.state]

          return (
            <div key={s.id} className="flex items-center justify-between rounded-lg border border-gray-800 bg-gray-900 p-4">
              <div>
                <p className="font-medium">{s.registration_number}</p>
                <p className="text-sm text-gray-400">
                  {s.guest_phone_number} · <span className="uppercase tracking-wide">{s.state.replace('_', ' ')}</span>
                  {s.key_tag ? ` · key ${s.key_tag}` : ''}
                </p>
              </div>

              {isUnaccepted && (
                <button
                  disabled={busyId === s.id}
                  onClick={() => void runAction(s, 'accept')}
                  className="rounded-md bg-emerald-600 px-3 py-1.5 text-sm font-medium hover:bg-emerald-500 disabled:opacity-50"
                >
                  Accept
                </button>
              )}

              {!isUnaccepted && isMine && next && (
                <button
                  disabled={busyId === s.id}
                  onClick={() =>
                    next.path === 'park' ? setParkingSession(s) : void runAction(s, next.path)
                  }
                  className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium hover:bg-indigo-500 disabled:opacity-50"
                >
                  {next.label}
                </button>
              )}

              {!isUnaccepted && !isMine && (
                <span className="text-sm text-gray-500">Accepted by another desk session</span>
              )}
            </div>
          )
        })}
      </div>

      {finished.length > 0 && (
        <div className="mt-8">
          <h2 className="mb-2 text-sm font-medium text-gray-400">Completed today</h2>
          <div className="space-y-1">
            {finished.map((s) => (
              <div key={s.id} className="rounded-md border border-gray-900 bg-gray-950 px-4 py-2 text-sm text-gray-500">
                {s.registration_number} — {s.state}
              </div>
            ))}
          </div>
        </div>
      )}
    </Layout>
  )
}
