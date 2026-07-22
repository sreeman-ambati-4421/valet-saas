import { useState, type FormEvent } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { apiFetch, ApiError } from '../lib/api'
import { PasswordInput } from '../components/PasswordInput'

export function AcceptInvite() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const token = params.get('token')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (!token) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-950 px-4 text-gray-400">
        Missing invite link.
      </div>
    )
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (password !== confirm) {
      setError('Passwords do not match')
      return
    }
    setSubmitting(true)
    setError(null)

    try {
      await apiFetch('/invites/accept', null, {
        method: 'POST',
        body: JSON.stringify({ token, password }),
      })
    } catch (err) {
      setSubmitting(false)
      setError(err instanceof ApiError ? err.message : 'Failed to accept invite')
      return
    }

    setSubmitting(false)
    navigate('/login', { replace: true })
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-950 px-4">
      <form onSubmit={handleSubmit} className="w-full max-w-sm space-y-4 rounded-xl border border-gray-800 bg-gray-900 p-8">
        <h1 className="text-xl font-semibold text-gray-100">Welcome — set your password</h1>
        <p className="text-sm text-gray-400">You've been invited to the Valet Parking platform. Choose a password to finish setting up your account.</p>

        <PasswordInput label="Password" value={password} onChange={setPassword} minLength={8} autoFocus />
        <PasswordInput label="Confirm password" value={confirm} onChange={setConfirm} minLength={8} />

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
