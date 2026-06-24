import { useEffect, useState } from 'react'
import { subscribe } from '../lib/toast'

// Listens to the toast bus and renders auto-dismissing toasts (bottom-right).
export default function Toaster() {
  const [items, setItems] = useState([])

  useEffect(() => subscribe((t) => {
    setItems((prev) => [...prev, t])
    setTimeout(() => setItems((prev) => prev.filter((x) => x.id !== t.id)), 4000)
  }), [])

  if (!items.length) return null
  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex flex-col gap-2">
      {items.map((t) => (
        <div
          key={t.id}
          className="pointer-events-auto max-w-xs rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200 shadow-xl shadow-black/40 backdrop-blur"
        >
          {t.message}
        </div>
      ))}
    </div>
  )
}
