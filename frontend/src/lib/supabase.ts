import { createClient } from '@supabase/supabase-js'

const url = import.meta.env.VITE_SUPABASE_URL as string
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string

if (!url || !anonKey) {
  console.warn(
    'VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY are not set. Copy .env.example to .env and fill in your Supabase project credentials.'
  )
}

// Sign-in is plain phone+password (signInWithPassword) -- no redirect links
// involved, so the default PKCE flow needs no override. The accept-invite
// link itself doesn't touch this client at all; it's verified by our own
// backend, not Supabase.
export const supabase = createClient(url, anonKey)
