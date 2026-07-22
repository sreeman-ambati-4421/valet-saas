import type { ReactNode } from 'react'
import { useAuth } from '../auth/AuthContext'

export function Layout({ title, children }: { title: string; children: ReactNode }) {
  const { me, signOut } = useAuth()

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <header className="flex items-center justify-between gap-3 border-b border-gray-800 px-4 py-3 sm:px-6 sm:py-4">
        <div className="min-w-0">
          <h1 className="truncate text-base font-semibold sm:text-lg">{title}</h1>
          {me && <p className="truncate text-xs text-gray-400 sm:text-sm">{me.full_name} · {me.role.replace('_', ' ')}</p>}
        </div>
        <button
          onClick={() => void signOut()}
          className="shrink-0 rounded-md border border-gray-700 px-3 py-1.5 text-sm text-gray-300 hover:bg-gray-800"
        >
          Sign out
        </button>
      </header>
      <main className="mx-auto max-w-5xl p-4 sm:p-6">{children}</main>
    </div>
  )
}
