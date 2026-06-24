import { useState } from 'react'

const inputCls =
  'w-full rounded-xl border border-white/10 bg-black/20 px-3.5 py-2.5 text-sm text-zinc-100 placeholder:text-zinc-600 outline-none transition focus:ring-2'

export default function AuthScreen({ sb, mode, endpoint, theme }) {
  const [tab, setTab] = useState('login') // 'login' | 'signup'
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [username, setUsername] = useState('')
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState(null) // { kind: 'error'|'info', text }

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setMsg(null)
    try {
      if (tab === 'signup') {
        const { data, error } = await sb.auth.signUp({
          email,
          password,
          options: { data: { username } },
        })
        if (error) throw error
        if (!data.session) setMsg({ kind: 'info', text: 'Account created. Check your email to confirm, then log in.' })
      } else {
        const { error } = await sb.auth.signInWithPassword({ email, password })
        if (error) throw error
        // success → onAuthStateChange in Portal swaps to the dashboard
      }
    } catch (err) {
      setMsg({ kind: 'error', text: err.message })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex min-h-[80vh] items-center justify-center p-4">
      <div className="w-full max-w-sm rounded-2xl border border-white/[0.06] bg-zinc-900/50 p-7 shadow-2xl shadow-black/50 backdrop-blur-xl">
        <div className="mb-5 flex items-center gap-2">
          <span className={`h-1.5 w-1.5 rounded-full ${theme.dot}`} />
          <span className={`text-[11px] font-semibold uppercase tracking-wider ${theme.text}`}>{mode} access</span>
        </div>

        <h1 className="mb-5 text-2xl font-semibold tracking-tight text-zinc-100">
          {tab === 'login' ? 'Welcome back' : 'Create account'}
        </h1>

        <div className="mb-5 flex gap-1 rounded-xl border border-white/5 bg-black/30 p-1 text-sm">
          {['login', 'signup'].map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => { setTab(t); setMsg(null) }}
              className={`flex-1 rounded-lg py-1.5 font-medium capitalize transition ${
                tab === t ? 'bg-white/10 text-zinc-100' : 'text-zinc-500 hover:text-zinc-300'
              }`}
            >
              {t}
            </button>
          ))}
        </div>

        <form onSubmit={submit} className="space-y-3">
          {tab === 'signup' && (
            <input
              className={`${inputCls} ${theme.ring}`}
              placeholder="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          )}
          <input
            type="email"
            className={`${inputCls} ${theme.ring}`}
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <input
            type="password"
            className={`${inputCls} ${theme.ring}`}
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={4}
            required
          />
          <button
            type="submit"
            disabled={busy}
            className={`w-full rounded-xl py-2.5 text-sm font-semibold transition disabled:opacity-50 ${theme.button}`}
          >
            {busy ? '…' : tab === 'login' ? 'Log in' : 'Create account'}
          </button>
        </form>

        {msg && (
          <p className={`mt-3 text-sm ${msg.kind === 'error' ? 'text-red-400' : 'text-emerald-400'}`}>
            {msg.text}
          </p>
        )}

        <p className="mt-6 break-all border-t border-white/[0.06] pt-4 font-mono text-[10px] text-zinc-600">
          {endpoint}
        </p>
      </div>
    </div>
  )
}
