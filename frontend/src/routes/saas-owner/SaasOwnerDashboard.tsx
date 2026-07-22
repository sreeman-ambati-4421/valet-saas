import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { useAuth } from '../../auth/AuthContext'
import { Layout } from '../../components/Layout'
import { apiFetch, ApiError } from '../../lib/api'
import type { Tenant } from '../../lib/types'

export function SaasOwnerDashboard() {
  const { session } = useAuth()
  const accessToken = session?.access_token ?? null
  const [tenants, setTenants] = useState<Tenant[]>([])

  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const [ownerName, setOwnerName] = useState('')
  const [ownerPhone, setOwnerPhone] = useState('')
  const [ownerTenantId, setOwnerTenantId] = useState('')
  const [ownerError, setOwnerError] = useState<string | null>(null)
  const [ownerMessage, setOwnerMessage] = useState<string | null>(null)
  const [ownerSubmitting, setOwnerSubmitting] = useState(false)

  const load = useCallback(async () => {
    if (!accessToken) return
    try {
      const data = await apiFetch<Tenant[]>('/tenants', accessToken)
      setTenants(data)
      setOwnerTenantId((current) => current || data[0]?.id || '')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to load tenants')
    }
  }, [accessToken])

  useEffect(() => {
    void load()
  }, [load])

  async function createTenant(e: FormEvent) {
    e.preventDefault()
    if (!accessToken || !name.trim()) return
    setSubmitting(true)
    setError(null)
    try {
      await apiFetch('/tenants', accessToken, {
        method: 'POST',
        body: JSON.stringify({ name: name.trim() }),
      })
      setName('')
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to create tenant')
    } finally {
      setSubmitting(false)
    }
  }

  async function inviteBusinessOwner(e: FormEvent) {
    e.preventDefault()
    if (!accessToken || !ownerPhone.trim() || !ownerTenantId) return
    setOwnerSubmitting(true)
    setOwnerError(null)
    setOwnerMessage(null)
    try {
      const result = await apiFetch<{ message: string }>(`/tenants/${ownerTenantId}/admins`, accessToken, {
        method: 'POST',
        body: JSON.stringify({ full_name: ownerName.trim(), phone_number: ownerPhone.trim() }),
      })
      setOwnerMessage(result.message)
      setOwnerName('')
      setOwnerPhone('')
    } catch (err) {
      setOwnerError(err instanceof ApiError ? err.message : 'Failed to send invite')
    } finally {
      setOwnerSubmitting(false)
    }
  }

  return (
    <Layout title="SaaS Owner">
      <h2 className="mb-2 text-sm font-medium text-gray-400">Tenants</h2>
      <form onSubmit={createTenant} className="mb-4 flex gap-3 rounded-lg border border-gray-800 bg-gray-900 p-4">
        <input
          required
          placeholder="Tenant / business name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="flex-1 rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={submitting}
          className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium hover:bg-indigo-500 disabled:opacity-50"
        >
          Create Tenant
        </button>
      </form>
      {error && <p className="mb-4 rounded-md bg-red-950 px-3 py-2 text-sm text-red-300">{error}</p>}

      <div className="mb-8 space-y-2">
        {tenants.length === 0 && <p className="text-gray-500">No tenants yet.</p>}
        {tenants.map((t) => (
          <div key={t.id} className="rounded-lg border border-gray-800 bg-gray-900 p-4">
            <p className="font-medium">{t.name}</p>
            <p className="text-xs text-gray-500">{t.id}</p>
          </div>
        ))}
      </div>

      <h2 className="mb-2 text-sm font-medium text-gray-400">Invite Business Owner</h2>
      {tenants.length === 0 ? (
        <p className="text-gray-500">Create a tenant first before inviting its business owner.</p>
      ) : (
        <>
        <form onSubmit={inviteBusinessOwner} className="grid grid-cols-1 gap-3 rounded-lg border border-gray-800 bg-gray-900 p-4 sm:grid-cols-3">
          <input
            required
            placeholder="Full name"
            value={ownerName}
            onChange={(e) => setOwnerName(e.target.value)}
            className="rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm"
          />
          <input
            required
            placeholder="WhatsApp number (+91...)"
            value={ownerPhone}
            onChange={(e) => setOwnerPhone(e.target.value)}
            className="rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm"
          />
          <select
            value={ownerTenantId}
            onChange={(e) => setOwnerTenantId(e.target.value)}
            className="rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm"
          >
            {tenants.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
          <button
            type="submit"
            disabled={ownerSubmitting}
            className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium hover:bg-indigo-500 disabled:opacity-50"
          >
            Send Invite
          </button>
        </form>
        <p className="mt-2 text-xs text-gray-500">
          They'll get a WhatsApp message (sandbox) with a link to set their password — the recipient's phone
          must have joined the Twilio Sandbox first. After that, they sign in with this number and password.
        </p>
        </>
      )}
      {ownerError && <p className="mt-4 rounded-md bg-red-950 px-3 py-2 text-sm text-red-300">{ownerError}</p>}
      {ownerMessage && <p className="mt-4 rounded-md bg-emerald-950 px-3 py-2 text-sm text-emerald-300">{ownerMessage}</p>}

      <p className="mt-8 text-sm text-gray-500">
        Full platform administration (subscriptions, health monitoring) is coming later. This is just enough to
        bootstrap a pilot tenant end to end.
      </p>
    </Layout>
  )
}
