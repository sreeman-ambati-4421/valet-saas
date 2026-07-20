import { useSearchParams } from 'react-router-dom'

// WhatsApp (and most messaging/email clients) auto-fetch a link's URL to
// generate a preview card the moment a message arrives -- before the
// recipient ever taps it. Supabase's single-use invite tokens treat that
// automated fetch as consumption, so the real tap then fails with an
// "expired" error. Routing through this page first means WhatsApp's
// preview-fetcher only ever sees this static page; the actual Supabase
// link is only requested on an explicit, real user click.
export function InviteRedirect() {
  const [params] = useSearchParams()
  const target = params.get('to')

  if (!target) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-950 px-4 text-gray-400">
        Missing invite link.
      </div>
    )
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-950 px-4">
      <div className="w-full max-w-sm space-y-4 rounded-xl border border-gray-800 bg-gray-900 p-8 text-center">
        <h1 className="text-xl font-semibold text-gray-100">You've been invited</h1>
        <p className="text-sm text-gray-400">Tap below to continue setting up your account.</p>
        <a
          href={target}
          className="inline-block w-full rounded-md bg-indigo-600 px-3 py-2 font-medium text-white hover:bg-indigo-500"
        >
          Continue
        </a>
      </div>
    </div>
  )
}
