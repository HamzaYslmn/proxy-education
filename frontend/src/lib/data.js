// MARK: Data access — each row's primary key IS the user's auth uid (id = auth.uid()).
// private.id is a FK back to public.id (the relationship that powers the JOIN demo).
// Works through the direct or proxied client; only the `sb` argument differs.

// Dedup concurrent ensure() calls (React StrictMode double-mounts effects in dev).
const _inflight = new Map()
function once(key, fn) {
  if (!_inflight.has(key)) _inflight.set(key, fn().finally(() => _inflight.delete(key)))
  return _inflight.get(key)
}

async function firstRow(sb, table, userId, cols) {
  const { data, error } = await sb
    .from(table)
    .select(cols)
    .eq('id', userId)
    .limit(1)
  if (error) throw error
  return data?.[0] ?? null
}

// Create the public profile first, then the private row (which references it via the id FK).
// We never send `id` — the DB defaults it to auth.uid() and RLS enforces id = auth.uid().
export function ensureSetup(sb, user, username) {
  return once(`setup:${user.id}`, async () => {
    const pub = await firstRow(sb, 'public', user.id, 'data')
    if (pub) return { pub, priv: await firstRow(sb, 'private', user.id, 'data') }

    const { data: pub2, error: e1 } = await sb
      .from('public')
      .insert({ data: { username, registered_at: new Date().toISOString() } })
      .select('data')
      .single()
    if (e1) throw e1

    const { data: priv, error: e2 } = await sb
      .from('private')
      .insert({ data: { notes: '' } })
      .select('id')
      .single()
    if (e2) throw e2

    return { pub: pub2, priv }
  })
}

export async function saveNotes(sb, user, notes) {
  const { error } = await sb
    .from('private')
    .update({ data: { notes } })
    .eq('id', user.id)
  if (error) throw error
}
