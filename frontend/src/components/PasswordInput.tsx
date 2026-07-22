import { useState } from 'react'

function EyeIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" className="h-4 w-4">
      <path strokeLinecap="round" strokeLinejoin="round" d="M1.5 10S4.5 4 10 4s8.5 6 8.5 6-3 6-8.5 6-8.5-6-8.5-6Z" />
      <circle cx="10" cy="10" r="2.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function EyeOffIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" className="h-4 w-4">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M3 3l14 14M8.3 8.4a2.5 2.5 0 0 0 3.4 3.4M6.2 6.1C3.7 7.5 1.5 10 1.5 10S4.5 16 10 16c1.4 0 2.6-.3 3.7-.8M11.9 5.4c-.6-.1-1.2-.2-1.9-.2 5.5 0 8.5 6 8.5 6s-.6 1.1-1.6 2.3"
      />
    </svg>
  )
}

export function PasswordInput({
  label,
  value,
  onChange,
  minLength,
  autoFocus,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  minLength?: number
  autoFocus?: boolean
}) {
  const [visible, setVisible] = useState(false)

  return (
    <div className="space-y-1">
      <label className="text-sm text-gray-400">{label}</label>
      <div className="relative">
        <input
          type={visible ? 'text' : 'password'}
          required
          minLength={minLength}
          autoFocus={autoFocus}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full rounded-md border border-gray-700 bg-gray-800 px-3 py-2 pr-10 text-gray-100 outline-none focus:border-indigo-500"
        />
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          tabIndex={-1}
          aria-label={visible ? 'Hide password' : 'Show password'}
          className="absolute inset-y-0 right-0 flex items-center px-3 text-gray-400 hover:text-gray-200"
        >
          {visible ? <EyeOffIcon /> : <EyeIcon />}
        </button>
      </div>
    </div>
  )
}
