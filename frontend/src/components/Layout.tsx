import type { ReactNode } from 'react'
import { useAuth } from '../auth/AuthContext'

export function Layout({ title, children }: { title: string; children: ReactNode }) {
  const { me, signOut } = useAuth()

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <header className="flex items-center justify-between border-b border-gray-800 px-6 py-4">
        <div>
          <h1 className="text-lg font-semibold">{title}</h1>
          {me && <p className="text-sm text-gray-400">{me.full_name} · {me.role.replace('_', ' ')}</p>}
        </div>
        <button
          onClick={() => void signOut()}
          className="rounded-md border border-gray-700 px-3 py-1.5 text-sm text-gray-300 hover:bg-gray-800"
        >
          Sign out
        </button>
      </header>
      <main className="mx-auto max-w-5xl p-6">{children}</main>
    </div>
  )
}
