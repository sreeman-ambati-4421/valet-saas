import { Navigate } from 'react-router-dom'
import type { ReactNode } from 'react'
import { useAuth } from './AuthContext'
import type { UserRole } from '../lib/types'

export function ProtectedRoute({
  allowedRoles,
  children,
}: {
  allowedRoles: UserRole[]
  children: ReactNode
}) {
  const { session, me, loading, meLoading } = useAuth()

  if (loading || meLoading) {
    return <div className="flex min-h-screen items-center justify-center text-gray-400">Loading…</div>
  }

  if (!session) {
    return <Navigate to="/login" replace />
  }

  if (!me) {
    return <div className="flex min-h-screen items-center justify-center text-red-400">Could not load your profile. Try signing in again.</div>
  }

  if (!allowedRoles.includes(me.role)) {
    return <Navigate to="/" replace />
  }

  return <>{children}</>
}
