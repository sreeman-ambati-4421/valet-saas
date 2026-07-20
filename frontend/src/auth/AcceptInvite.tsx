import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { supabase } from '../lib/supabase'
import { apiFetch, ApiError } from '../lib/api'

export function AcceptInvite() {
  const navigate = useNavigate()
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (password !== confirm) {
      setError('Passwords do not match')
      return
    }
    setSubmitting(true)
    setError(null)

    const { error: updateError } = await supabase.auth.updateUser({ password })
    if (updateError) {
      setSubmitting(false)
      setError(updateError.message)
      return
    }

    // Setting the password proves they control the account -- that's what
    // actually activates them in our own users table, not the invite
    // merely having been sent.
    const { data } = await supabase.auth.getSession()
    const accessToken = data.session?.access_token ?? null
    try {
      await apiFetch('/me/confirm', accessToken, { method: 'POST' })
    } catch (err) {
      setSubmitting(false)
      setError(
        err instanceof ApiError
          ? `Password was set, but activating your account failed: ${err.message}. Try submitting again.`
          : 'Password was set, but activating your account failed. Try submitting again.'
      )
      return
    }

    setSubmitting(false)
    navigate('/', { replace: true })
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-950 px-4">
      <form onSubmit={handleSubmit} className="w-full max-w-sm space-y-4 rounded-xl border border-gray-800 bg-gray-900 p-8">
        <h1 className="text-xl font-semibold text-gray-100">Welcome — set your password</h1>
        <p className="text-sm text-gray-400">You've been invited to the Valet Parking platform. Choose a password to finish setting up your account.</p>

        <div className="space-y-1">
          <label className="text-sm text-gray-400">Password</label>
          <input
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-gray-100 outline-none focus:border-indigo-500"
          />
        </div>

        <div className="space-y-1">
          <label className="text-sm text-gray-400">Confirm password</label>
          <input
            type="password"
            required
            minLength={8}
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            className="w-full rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-gray-100 outline-none focus:border-indigo-500"
          />
        </div>

        {error && <p className="text-sm text-red-400">{error}</p>}

        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-md bg-indigo-600 px-3 py-2 font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
        >
          {submitting ? 'Saving…' : 'Set password & continue'}
        </button>
      </form>
    </div>
  )
}
