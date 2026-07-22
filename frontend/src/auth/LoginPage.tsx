import { useState, type FormEvent } from 'react'
import { supabase } from '../lib/supabase'

export function LoginPage() {
  const [step, setStep] = useState<'phone' | 'code'>('phone')
  const [phone, setPhone] = useState('')
  const [code, setCode] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function sendCode(e: FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    const { error } = await supabase.auth.signInWithOtp({ phone })
    setSubmitting(false)
    if (error) {
      setError(error.message)
      return
    }
    setStep('code')
  }

  async function verifyCode(e: FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    const { error } = await supabase.auth.verifyOtp({ phone, token: code, type: 'sms' })
    setSubmitting(false)
    if (error) setError(error.message)
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-950 px-4">
      <div className="w-full max-w-sm space-y-4 rounded-xl border border-gray-800 bg-gray-900 p-8">
        <h1 className="text-xl font-semibold text-gray-100">Valet Parking — Sign in</h1>
        <p className="text-sm text-gray-400">
          {step === 'phone'
            ? "We'll send a one-time code to this number on WhatsApp."
            : `Enter the code sent to ${phone} on WhatsApp.`}
        </p>

        {step === 'phone' ? (
          <form onSubmit={sendCode} className="space-y-4">
            <div className="space-y-1">
              <label className="text-sm text-gray-400">WhatsApp number</label>
              <input
                type="tel"
                required
                autoFocus
                placeholder="+919999999999"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                className="w-full rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-gray-100 outline-none focus:border-indigo-500"
              />
            </div>

            {error && <p className="text-sm text-red-400">{error}</p>}

            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-md bg-indigo-600 px-3 py-2 font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
            >
              {submitting ? 'Sending…' : 'Send code'}
            </button>
          </form>
        ) : (
          <form onSubmit={verifyCode} className="space-y-4">
            <div className="space-y-1">
              <label className="text-sm text-gray-400">Code</label>
              <input
                type="text"
                inputMode="numeric"
                required
                autoFocus
                value={code}
                onChange={(e) => setCode(e.target.value)}
                className="w-full rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-gray-100 outline-none focus:border-indigo-500"
              />
            </div>

            {error && <p className="text-sm text-red-400">{error}</p>}

            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-md bg-indigo-600 px-3 py-2 font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
            >
              {submitting ? 'Verifying…' : 'Verify & sign in'}
            </button>
            <button
              type="button"
              onClick={() => {
                setStep('phone')
                setCode('')
                setError(null)
              }}
              className="w-full text-sm text-gray-400 hover:text-gray-300"
            >
              Use a different number
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
