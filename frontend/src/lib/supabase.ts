import { createClient } from '@supabase/supabase-js'

const url = import.meta.env.VITE_SUPABASE_URL as string
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string

if (!url || !anonKey) {
  console.warn(
    'VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY are not set. Copy .env.example to .env and fill in your Supabase project credentials.'
  )
}

// Sign-in is WhatsApp-OTP based (signInWithOtp + verifyOtp), entirely
// within a single browser session -- no redirect links involved, so the
// default PKCE flow needs no override.
export const supabase = createClient(url, anonKey)
