import { useEffect, useState } from 'react'
import { ensureSetup, saveNotes } from '../lib/data'

const cardCls = 'rounded-2xl border border-white/[0.06] bg-zinc-900/40 p-6 shadow-xl shadow-black/30 backdrop-blur'
const labelCls = 'text-[11px] font-semibold uppercase tracking-wider text-zinc-500'

export default function Dashboard({ sb, user, mode, endpoint, theme }) {
  const [profile, setProfile] = useState(null)
  const [notes, setNotes] = useState('')
  const [state, setState] = useState('loading') // 'loading' | 'ready' | error string
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    let alive = true
    ;(async () => {
      try {
        const { pub, priv } = await ensureSetup(sb, user, user.user_metadata?.username || user.email)
        if (!alive) return
        setProfile(pub.data)
        setNotes(priv?.data?.notes || '')
        setState('ready')
      } catch (err) {
        if (alive) setState(`error: ${err.message}`)
      }
    })()
    return () => { alive = false }
  }, [sb, user])

  const save = async () => {
    setSaving(true)
    setSaved(false)
    try {
      await saveNotes(sb, user, notes)
      setSaved(true)
    } catch (err) {
      setState(`error: ${err.message}`)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="mx-auto max-w-2xl p-4 sm:p-8">
      <header className="mb-7 flex items-center justify-between">
        <div>
          <div className="mb-1 flex items-center gap-2">
            <span className={`h-1.5 w-1.5 rounded-full ${theme.dot}`} />
            <span className={`text-[11px] font-semibold uppercase tracking-wider ${theme.text}`}>{mode} access</span>
          </div>
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-100">Dashboard</h1>
        </div>
        <button
          onClick={() => sb.auth.signOut()}
          className="rounded-xl border border-white/10 px-3.5 py-2 text-sm text-zinc-300 transition hover:bg-white/5 hover:text-zinc-100"
        >
          Sign out
        </button>
      </header>

      {state === 'loading' && <p className="text-sm text-zinc-600">Loading…</p>}
      {typeof state === 'string' && state.startsWith('error') && (
        <p className="text-sm text-red-400">{state}</p>
      )}

      {state === 'ready' && (
        <div className="space-y-5">
          {/* public — username + registration date */}
          <section className={cardCls}>
            <h2 className={`mb-4 ${labelCls}`}>Public profile</h2>
            <dl className="grid grid-cols-[7rem_1fr] gap-y-3 text-sm">
              <dt className="text-zinc-500">Username</dt>
              <dd className="font-medium text-zinc-100">{profile?.username}</dd>
              <dt className="text-zinc-500">Email</dt>
              <dd className="text-zinc-300">{user.email}</dd>
              <dt className="text-zinc-500">Registered</dt>
              <dd className="text-zinc-300">
                {profile?.registered_at ? new Date(profile.registered_at).toLocaleString() : '—'}
              </dd>
            </dl>
          </section>

          {/* private — notes */}
          <section className={cardCls}>
            <h2 className={`mb-4 ${labelCls}`}>Private notes</h2>
            <textarea
              value={notes}
              onChange={(e) => { setNotes(e.target.value); setSaved(false) }}
              rows={6}
              placeholder="Only you can read this…"
              className={`w-full resize-none rounded-xl border border-white/10 bg-black/20 px-3.5 py-3 text-sm leading-relaxed text-zinc-100 placeholder:text-zinc-600 outline-none transition focus:ring-2 ${theme.ring}`}
            />
            <div className="mt-4 flex items-center gap-3">
              <button
                onClick={save}
                disabled={saving}
                className={`rounded-xl px-4 py-2 text-sm font-semibold transition disabled:opacity-50 ${theme.button}`}
              >
                {saving ? 'Saving…' : 'Save notes'}
              </button>
              {saved && <span className="text-sm text-emerald-400">Saved ✓</span>}
            </div>
          </section>

          <p className="break-all px-1 font-mono text-[10px] text-zinc-600">via {endpoint}</p>
        </div>
      )}
    </div>
  )
}
