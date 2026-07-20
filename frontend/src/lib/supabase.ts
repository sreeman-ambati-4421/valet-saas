import { createClient } from '@supabase/supabase-js'

const url = import.meta.env.VITE_SUPABASE_URL as string
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string

if (!url || !anonKey) {
  console.warn(
    'VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY are not set. Copy .env.example to .env and fill in your Supabase project credentials.'
  )
}

// PKCE (the client's default flow) doesn't support invite/magic links --
// it requires the same browser/device to both start and finish the auth
// flow, which breaks for a link generated on our backend and clicked on
// the recipient's own phone via WhatsApp. Implicit flow has no such
// same-device requirement.
export const supabase = createClient(url, anonKey, {
  auth: { flowType: 'implicit' },
})
