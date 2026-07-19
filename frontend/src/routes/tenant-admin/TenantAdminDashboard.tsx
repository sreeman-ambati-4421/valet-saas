import { useState, type FormEvent } from 'react'
import { useAuth } from '../../auth/AuthContext'
import { Layout } from '../../components/Layout'
import { apiFetch, ApiError } from '../../lib/api'

export function TenantAdminDashboard() {
  const { session, me, refreshMe } = useAuth()
  const accessToken = session?.access_token ?? null

  const [venueName, setVenueName] = useState('')
  const [venueAddress, setVenueAddress] = useState('')
  const [venueError, setVenueError] = useState<string | null>(null)
  const [venueSubmitting, setVenueSubmitting] = useState(false)

  const [staffEmail, setStaffEmail] = useState('')
  const [staffName, setStaffName] = useState('')
  const [staffRole, setStaffRole] = useState<'venue_manager' | 'valet'>('valet')
  const [staffVenueId, setStaffVenueId] = useState(me?.venues[0]?.id ?? '')
  const [staffError, setStaffError] = useState<string | null>(null)
  const [staffMessage, setStaffMessage] = useState<string | null>(null)
  const [staffSubmitting, setStaffSubmitting] = useState(false)

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

  async function inviteStaff(e: FormEvent) {
    e.preventDefault()
    if (!accessToken || !staffEmail.trim() || !staffVenueId) return
    setStaffSubmitting(true)
    setStaffError(null)
    setStaffMessage(null)
    try {
      const result = await apiFetch<{ message: string }>(`/venues/${staffVenueId}/staff`, accessToken, {
        method: 'POST',
        body: JSON.stringify({ email: staffEmail.trim(), full_name: staffName.trim(), role: staffRole }),
      })
      setStaffMessage(result.message)
      setStaffEmail('')
      setStaffName('')
    } catch (err) {
      setStaffError(err instanceof ApiError ? err.message : 'Failed to send invite')
    } finally {
      setStaffSubmitting(false)
    }
  }

  return (
    <Layout title="Tenant Admin">
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

      <div className="mb-8 space-y-2">
        {(!me || me.venues.length === 0) && <p className="text-gray-500">No venues yet.</p>}
        {me?.venues.map((v) => (
          <div key={v.id} className="rounded-lg border border-gray-800 bg-gray-900 p-4">
            <p className="font-medium">{v.name}</p>
            <p className="text-xs text-gray-500">{v.id}</p>
          </div>
        ))}
      </div>

      <h2 className="mb-2 text-sm font-medium text-gray-400">Invite Staff</h2>
      {!me || me.venues.length === 0 ? (
        <p className="text-gray-500">Create a venue first before inviting staff.</p>
      ) : (
        <form onSubmit={inviteStaff} className="grid grid-cols-1 gap-3 rounded-lg border border-gray-800 bg-gray-900 p-4 sm:grid-cols-5">
          <input
            required
            type="email"
            placeholder="Email"
            value={staffEmail}
            onChange={(e) => setStaffEmail(e.target.value)}
            className="rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm"
          />
          <input
            required
            placeholder="Full name"
            value={staffName}
            onChange={(e) => setStaffName(e.target.value)}
            className="rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm"
          />
          <select
            value={staffRole}
            onChange={(e) => setStaffRole(e.target.value as 'venue_manager' | 'valet')}
            className="rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm"
          >
            <option value="valet">Valet</option>
            <option value="venue_manager">Venue Manager</option>
          </select>
          <select
            value={staffVenueId}
            onChange={(e) => setStaffVenueId(e.target.value)}
            className="rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm"
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
      )}
      {staffError && <p className="mt-4 rounded-md bg-red-950 px-3 py-2 text-sm text-red-300">{staffError}</p>}
      {staffMessage && <p className="mt-4 rounded-md bg-emerald-950 px-3 py-2 text-sm text-emerald-300">{staffMessage}</p>}
    </Layout>
  )
}
