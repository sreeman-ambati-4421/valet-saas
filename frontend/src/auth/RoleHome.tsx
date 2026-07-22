import { Navigate } from 'react-router-dom'
import { useAuth } from './AuthContext'

const ROLE_HOME: Record<string, string> = {
  saas_owner: '/saas-owner',
  business_owner: '/business-owner',
  valet_desk: '/valet-desk',
}

export function RoleHome() {
  const { session, me, loading } = useAuth()

  if (loading) {
    return <div className="flex min-h-screen items-center justify-center text-gray-400">Loading…</div>
  }
  if (!session) return <Navigate to="/login" replace />
  if (!me) return <Navigate to="/login" replace />

  return <Navigate to={ROLE_HOME[me.role] ?? '/login'} replace />
}
