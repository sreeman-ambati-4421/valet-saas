import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { useAuth } from '../../auth/AuthContext'
import { Layout } from '../../components/Layout'
import { apiFetch, ApiError, API_URL } from '../../lib/api'
import type { QRCode, SessionState, ValetSession } from '../../lib/types'

const POLL_MS = 5000

const ALL_STATES: SessionState[] = [
  'REQUESTED',
  'ACCEPTED',
  'PARKED',
  'RETRIEVAL_REQUESTED',
  'RETRIEVING',
  'READY',
  'COMPLETED',
  'CANCELLED',
]

export function BusinessOwnerDashboard() {
  const { session, me, refreshMe } = useAuth()
  const accessToken = session?.access_token ?? null

  const [venueName, setVenueName] = useState('')
  const [venueAddress, setVenueAddress] = useState('')
  const [venueError, setVenueError] = useState<string | null>(null)
  const [venueSubmitting, setVenueSubmitting] = useState(false)

  const [expandedVenueId, setExpandedVenueId] = useState<string | null>(null)
  const [tagsByVenue, setTagsByVenue] = useState<Record<string, QRCode[]>>({})
  const [tagCount, setTagCount] = useState(10)
  const [tagError, setTagError] = useState<string | null>(null)
  const [tagLoadingVenueId, setTagLoadingVenueId] = useState<string | null>(null)

  const [staffName, setStaffName] = useState('')
  const [staffPhone, setStaffPhone] = useState('')
  const [staffVenueId, setStaffVenueId] = useState(me?.venues[0]?.id ?? '')
  const [staffError, setStaffError] = useState<string | null>(null)
  const [staffMessage, setStaffMessage] = useState<string | null>(null)
  const [staffSubmitting, setStaffSubmitting] = useState(false)

  const [overviewVenueId, setOverviewVenueId] = useState<string | null>(me?.venues[0]?.id ?? null)
  const [sessions, setSessions] = useState<ValetSession[]>([])
  const [stateFilter, setStateFilter] = useState<SessionState | ''>('')
  const [regFilter, setRegFilter] = useState('')
  const [overviewError, setOverviewError] = useState<string | null>(null)

  const loadSessions = useCallback(async () => {
    if (!overviewVenueId || !accessToken) return
    const params = new URLSearchParams()
    if (stateFilter) params.set('state', stateFilter)
    if (regFilter) params.set('registration_number', regFilter)
    try {
      const data = await apiFetch<ValetSession[]>(
        `/venues/${overviewVenueId}/sessions?${params.toString()}`,
        accessToken
      )
      setSessions(data)
      setOverviewError(null)
    } catch (err) {
      setOverviewError(err instanceof ApiError ? err.message : 'Failed to load sessions')
    }
  }, [overviewVenueId, accessToken, stateFilter, regFilter])

  useEffect(() => {
    void loadSessions()
    const interval = setInterval(() => void loadSessions(), POLL_MS)
    return () => clearInterval(interval)
  }, [loadSessions])

  async function createVenue(e: FormEvent) {
    e.preventDefault()
    if (!accessToken || !venueName.trim()) return
    setVenueSubmitting(true)
    setVenueError(null)
    try {
      await apiFetch('/venues', accessToken, {
        method: 'POST',
        body: JSON.stringify({ name: venueName.trim(), address: venueAddress.trim() || null }),
      })
      setVenueName('')
      setVenueAddress('')
      await refreshMe()
    } catch (err) {
      setVenueError(err instanceof ApiError ? err.message : 'Failed to create venue')
    } finally {
      setVenueSubmitting(false)
    }
  }

  async function loadTags(venueId: string) {
    if (!accessToken) return
    try {
      const tags = await apiFetch<QRCode[]>(`/venues/${venueId}/qr-codes`, accessToken)
      setTagsByVenue((prev) => ({ ...prev, [venueId]: tags }))
    } catch (err) {
      setTagError(err instanceof ApiError ? err.message : 'Failed to load tags')
    }
  }

  function toggleVenueTags(venueId: string) {
    const next = expandedVenueId === venueId ? null : venueId
    setExpandedVenueId(next)
    if (next) void loadTags(next)
  }

  async function generateTags(venueId: string) {
    if (!accessToken || tagCount < 1) return
    setTagLoadingVenueId(venueId)
    setTagError(null)
    try {
      await apiFetch<QRCode[]>(`/venues/${venueId}/qr-codes`, accessToken, {
        method: 'POST',
        body: JSON.stringify({ count: tagCount }),
      })
      await loadTags(venueId)
    } catch (err) {
      setTagError(err instanceof ApiError ? err.message : 'Failed to generate tags')
    } finally {
      setTagLoadingVenueId(null)
    }
  }

  async function inviteStaff(e: FormEvent) {
    e.preventDefault()
    if (!accessToken || !staffPhone.trim() || !staffVenueId) return
    setStaffSubmitting(true)
    setStaffError(null)
    setStaffMessage(null)
    try {
      const result = await apiFetch<{ message: string }>(`/venues/${staffVenueId}/staff`, accessToken, {
        method: 'POST',
        body: JSON.stringify({
          full_name: staffName.trim(),
          phone_number: staffPhone.trim(),
        }),
      })
      setStaffMessage(result.message)
      setStaffName('')
      setStaffPhone('')
    } catch (err) {
      setStaffError(err instanceof ApiError ? err.message : 'Failed to send invite')
    } finally {
      setStaffSubmitting(false)
    }
  }

  return (
    <Layout title="Business Owner">
      <h2 className="mb-2 text-sm font-medium text-gray-400">Venues</h2>
      <form onSubmit={createVenue} className="mb-4 grid grid-cols-1 gap-3 rounded-lg border border-gray-800 bg-gray-900 p-4 sm:grid-cols-3">
        <input
          required
          placeholder="Venue name"
          value={venueName}
          onChange={(e) => setVenueName(e.target.value)}
          className="rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm"
        />
        <input
          placeholder="Address (optional)"
          value={venueAddress}
          onChange={(e) => setVenueAddress(e.target.value)}
          className="rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={venueSubmitting}
          className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium hover:bg-indigo-500 disabled:opacity-50"
        >
          Create Venue
        </button>
      </form>
      {venueError && <p className="mb-4 rounded-md bg-red-950 px-3 py-2 text-sm text-red-300">{venueError}</p>}

      {tagError && <p className="mb-4 rounded-md bg-red-950 px-3 py-2 text-sm text-red-300">{tagError}</p>}

      <div className="mb-8 space-y-2">
        {(!me || me.venues.length === 0) && <p className="text-gray-500">No venues yet.</p>}
        {me?.venues.map((v) => {
          const isExpanded = expandedVenueId === v.id
          const tags = tagsByVenue[v.id] ?? []
          const availableCount = tags.filter((t) => t.status === 'available').length
          return (
            <div key={v.id} className="rounded-lg border border-gray-800 bg-gray-900 p-4">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0">
                  <p className="truncate font-medium">{v.name}</p>
                  <p className="truncate text-xs text-gray-500">{v.id}</p>
                </div>
                <button
                  onClick={() => toggleVenueTags(v.id)}
                  className="shrink-0 self-start rounded-md border border-gray-700 px-3 py-1.5 text-sm hover:bg-gray-800 sm:self-auto"
                >
                  {isExpanded ? 'Hide Tags' : 'Manage Key Tags'}
                </button>
              </div>

              {isExpanded && (
                <div className="mt-4 space-y-4 border-t border-gray-800 pt-4">
                  <p className="text-sm text-gray-400">
                    {tags.length} tag{tags.length === 1 ? '' : 's'} total, {availableCount} available.
                  </p>

                  <div className="flex flex-wrap items-center gap-3">
                    <input
                      type="number"
                      min={1}
                      max={100}
                      value={tagCount}
                      onChange={(e) => setTagCount(Number(e.target.value))}
                      className="w-24 rounded-md border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm"
                    />
                    <button
                      onClick={() => void generateTags(v.id)}
                      disabled={tagLoadingVenueId === v.id}
                      className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium hover:bg-indigo-500 disabled:opacity-50"
                    >
                      {tagLoadingVenueId === v.id ? 'Generating…' : 'Generate Tags'}
                    </button>
                  </div>

                  {tags.length > 0 && (
                    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                      {tags.map((tag) => (
                        <div key={tag.id} className="rounded-md border border-gray-800 bg-gray-950 p-2 text-center">
                          <img
                            src={`${API_URL}/qr-codes/${tag.id}/image`}
                            alt={tag.label ?? tag.id}
                            className="mx-auto h-24 w-24 rounded bg-white p-1"
                          />
                          <p className="mt-1 text-xs font-medium">{tag.label}</p>
                          <p
                            className={`text-xs ${tag.status === 'available' ? 'text-emerald-400' : 'text-amber-400'}`}
                          >
                            {tag.status === 'available' ? 'Available' : 'In use'}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                  <p className="text-xs text-gray-500">
                    Print each QR + label onto a plastic key tag. Guests scan it on arrival to start their
                    WhatsApp request; the driver keeps the same tag attached to the keys until pickup.
                  </p>
                </div>
              )}
            </div>
          )
        })}
      </div>

      <h2 className="mb-2 text-sm font-medium text-gray-400">Invite Valet Desk Staff</h2>
      {!me || me.venues.length === 0 ? (
        <p className="text-gray-500">Create a venue first before inviting staff.</p>
      ) : (
        <>
        <form onSubmit={inviteStaff} className="grid grid-cols-1 gap-3 rounded-lg border border-gray-800 bg-gray-900 p-4 sm:grid-cols-3">
          <input
            required
            placeholder="Full name"
            value={staffName}
            onChange={(e) => setStaffName(e.target.value)}
            className="rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm"
          />
          <input
            required
            placeholder="WhatsApp number (+91...)"
            value={staffPhone}
            onChange={(e) => setStaffPhone(e.target.value)}
            className="rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm"
          />
          <select
            value={staffVenueId}
            onChange={(e) => setStaffVenueId(e.target.value)}
            className="rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm sm:col-span-2"
          >
            {me.venues.map((v) => (
              <option key={v.id} value={v.id}>
                {v.name}
              </option>
            ))}
          </select>
          <button
            type="submit"
            disabled={staffSubmitting}
            className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium hover:bg-indigo-500 disabled:opacity-50"
          >
            Send Invite
          </button>
        </form>
        <p className="mt-2 text-xs text-gray-500">
          They'll get a WhatsApp message with a link to set their password, then sign in with this number and
          password.
        </p>
        </>
      )}
      {staffError && <p className="mt-4 rounded-md bg-red-950 px-3 py-2 text-sm text-red-300">{staffError}</p>}
      {staffMessage && <p className="mt-4 rounded-md bg-emerald-950 px-3 py-2 text-sm text-emerald-300">{staffMessage}</p>}

      <h2 className="mt-10 mb-2 text-sm font-medium text-gray-400">Session Overview</h2>
      {(!me || me.venues.length === 0) ? (
        <p className="text-gray-500">No venues assigned yet.</p>
      ) : (
        <>
          <div className="mb-4 flex flex-wrap gap-3">
            {me.venues.length > 1 && (
              <select
                value={overviewVenueId ?? ''}
                onChange={(e) => setOverviewVenueId(e.target.value)}
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

          {overviewError && <p className="mb-4 rounded-md bg-red-950 px-3 py-2 text-sm text-red-300">{overviewError}</p>}

          <div className="overflow-x-auto rounded-lg border border-gray-800">
            <table className="w-full text-left text-sm">
              <thead className="bg-gray-900 text-gray-400">
                <tr>
                  <th className="px-4 py-2">Reg. Number</th>
                  <th className="px-4 py-2">Guest Phone</th>
                  <th className="px-4 py-2">State</th>
                  <th className="px-4 py-2">Tag</th>
                  <th className="px-4 py-2">Updated</th>
                </tr>
              </thead>
              <tbody>
                {sessions.map((s) => (
                  <tr key={s.id} className="border-t border-gray-800">
                    <td className="px-4 py-2 font-medium">{s.registration_number ?? '—'}</td>
                    <td className="px-4 py-2 text-gray-400">{s.guest_phone_number}</td>
                    <td className="px-4 py-2 uppercase tracking-wide text-gray-300">{s.state.replace('_', ' ')}</td>
                    <td className="px-4 py-2 text-gray-400">{s.tag_label ?? '—'}</td>
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
        </>
      )}
    </Layout>
  )
}
