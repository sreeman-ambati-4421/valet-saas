import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import type { Session } from '@supabase/supabase-js'
import { supabase } from '../lib/supabase'
import { apiFetch } from '../lib/api'
import type { Me } from '../lib/types'

interface AuthContextValue {
  session: Session | null
  me: Me | null
  loading: boolean
  error: string | null
  signOut: () => Promise<void>
  refreshMe: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null)
  const [me, setMe] = useState<Me | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function loadMe(accessToken: string) {
    try {
      const profile = await apiFetch<Me>('/me', accessToken)
      setMe(profile)
      setError(null)
    } catch (err) {
      setMe(null)
      setError(err instanceof Error ? err.message : 'Failed to load profile')
    }
  }

  useEffect(() => {
    let mounted = true

    supabase.auth.getSession().then(async ({ data }) => {
      if (!mounted) return
      setSession(data.session)
      if (data.session) await loadMe(data.session.access_token)
      setLoading(false)
    })

    const { data: listener } = supabase.auth.onAuthStateChange(async (_event, newSession) => {
      setSession(newSession)
      if (newSession) {
        await loadMe(newSession.access_token)
      } else {
        setMe(null)
      }
    })

    return () => {
      mounted = false
      listener.subscription.unsubscribe()
    }
  }, [])

  async function signOut() {
    await supabase.auth.signOut()
    setSession(null)
    setMe(null)
  }

  async function refreshMe() {
    if (session) await loadMe(session.access_token)
  }

  return (
    <AuthContext.Provider value={{ session, me, loading, error, signOut, refreshMe }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
