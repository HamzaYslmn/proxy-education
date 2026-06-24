import { useEffect, useState } from 'react'
import AuthScreen from './AuthScreen'
import Dashboard from './Dashboard'

// Auth gate: shows the dashboard when a session exists, the auth screen otherwise.
// `sb` is whichever client (direct or proxied) — everything below is identical.
export default function Portal({ sb, mode, endpoint, theme }) {
  const [session, setSession] = useState(undefined) // undefined = still checking

  useEffect(() => {
    sb.auth.getSession().then(({ data }) => setSession(data.session))
    // supabase-js re-emits auth events (focus, refresh ticks); keep the same object when the token
    // is unchanged so the dashboard doesn't refetch on every redundant event.
    const { data: { subscription } } = sb.auth.onAuthStateChange((_e, s) =>
      setSession((prev) => (prev?.access_token === s?.access_token ? prev : s)),
    )
    return () => subscription.unsubscribe()
  }, [sb])

  if (session === undefined) {
    return (
      <div className="flex items-center justify-center py-32 text-sm text-zinc-600">
        <span className={`mr-2 h-1.5 w-1.5 rounded-full ${theme.dot} animate-pulse`} />
        Connecting…
      </div>
    )
  }

  const props = { sb, mode, endpoint, theme }
  return session ? <Dashboard user={session.user} {...props} /> : <AuthScreen {...props} />
}
