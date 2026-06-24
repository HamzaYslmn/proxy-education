import { useState } from 'react'
import Portal from './components/Portal'
import Toaster from './components/Toaster'
import { MODES } from './lib/clients'

export default function App() {
  // persist the switch across refreshes; fall back to 'direct' if storage is empty/garbage
  const [mode, setMode] = useState(() => {
    const saved = localStorage.getItem('edu_mode')
    return MODES[saved] ? saved : 'direct'
  })
  const m = MODES[mode]

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-10 flex items-center justify-between px-5 py-3 border-b border-white/[0.06] bg-zinc-950/70 backdrop-blur-xl">
        <div className="flex items-center gap-2.5">
          <span className={`h-2 w-2 rounded-full ${m.theme.dot} shadow-[0_0_8px] ${m.theme.text}`} />
          <span className="text-sm font-medium tracking-tight text-zinc-200">Proxy vs Direct</span>
        </div>

        <div className="flex gap-1 rounded-xl border border-white/5 bg-black/30 p-1">
          {Object.entries(MODES).map(([key, cfg]) => (
            <button
              key={key}
              type="button"
              onClick={() => { setMode(key); localStorage.setItem('edu_mode', key) }}
              className={`flex items-center gap-2 rounded-lg px-3.5 py-1.5 text-sm font-medium transition ${
                mode === key ? 'bg-white/10 text-zinc-100' : 'text-zinc-500 hover:text-zinc-300'
              }`}
            >
              <span className={`h-1.5 w-1.5 rounded-full ${cfg.theme.dot}`} />
              {cfg.label}
            </button>
          ))}
        </div>
      </header>

      {/* key=mode → remount so each client re-checks its own session */}
      <Portal key={mode} sb={m.sb} mode={m.label} endpoint={m.endpoint} theme={m.theme} />
      <Toaster />
    </div>
  )
}
