import { createClient } from '@supabase/supabase-js'
import { toast } from './toast'

// MARK: Toast every failed request in one place — both clients route through this fetch.
async function fetchWithToasts(input, init) {
  let res
  try {
    res = await fetch(input, init)
  } catch (e) {
    toast('Network error — is the server reachable?')
    throw e
  }
  if (res.status === 429) toast('Too many requests — please slow down.')
  else if (!res.ok) {
    let msg = `Request failed (${res.status})`
    try {
      const b = await res.clone().json()
      msg = b.message || b.error_description || b.msg || (typeof b.error === 'string' ? b.error : msg)
    } catch { /* non-JSON body */ }
    toast(msg)
  }
  return res
}

const global = { fetch: fetchWithToasts }

// MARK: Direct — talks straight to Supabase (RLS enforced by Supabase on the user JWT)
export const DIRECT_URL = import.meta.env.SUPABASE_URL

export const directClient = createClient(
  import.meta.env.SUPABASE_URL,
  import.meta.env.SUPABASE_PUBLISHABLE_KEY,
  { auth: { storageKey: 'edu_direct' }, global },
)

// MARK: Proxied — same supabase-js, pointed at our backend which mirrors /rest/v1 and /auth/v1
// localhost:8001 in dev, same-origin rootpath in the cloud.
export const PROXY_URL = import.meta.env.DEV
  ? 'http://localhost:8001/api/db'
  : `${window.location.origin}/api/db`

export const proxiedClient = createClient(PROXY_URL, 'proxy-key', {
  global,
  auth: {
    storageKey: 'edu_proxied',
    // ponytail: no-op Web Lock — supabase-js v2's lock hangs on refresh through a proxy (customer-project fix)
    lock: (_name, _ttl, fn) => fn(),
  },
})

// MARK: Mode registry — the top-bar switch picks one. Theme classes are literal so Tailwind keeps them.
export const MODES = {
  direct: {
    label: 'Direct',
    sb: directClient,
    endpoint: DIRECT_URL,
    theme: {
      dot: 'bg-emerald-400',
      text: 'text-emerald-400',
      button: 'bg-emerald-500/90 hover:bg-emerald-400 text-zinc-950 shadow-lg shadow-emerald-500/20',
      ring: 'focus:border-emerald-500/50 focus:ring-emerald-500/15',
    },
  },
  proxied: {
    label: 'Proxied',
    sb: proxiedClient,
    endpoint: PROXY_URL,
    theme: {
      dot: 'bg-violet-400',
      text: 'text-violet-400',
      button: 'bg-violet-500/90 hover:bg-violet-400 text-white shadow-lg shadow-violet-500/20',
      ring: 'focus:border-violet-500/50 focus:ring-violet-500/15',
    },
  },
}
