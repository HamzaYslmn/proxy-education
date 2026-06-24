// Minimal toast bus — call toast(msg) from anywhere; <Toaster/> renders them.
// Dedupes the same message within 3s so a burst (e.g. repeated 429s) shows once.
let listeners = []
let seq = 0
let last = { message: null, at: 0 }

export function toast(message) {
  const now = Date.now()
  if (message === last.message && now - last.at < 3000) return
  last = { message, at: now }
  const t = { id: ++seq, message }
  listeners.forEach((fn) => fn(t))
}

export function subscribe(fn) {
  listeners.push(fn)
  return () => { listeners = listeners.filter((l) => l !== fn) }
}
