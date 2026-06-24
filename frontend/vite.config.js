import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import dotenv from 'dotenv'

const env = dotenv.config({ path: 'public.env' }).parsed ?? {}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  // dotenv → expose public.env keys as import.meta.env.SUPABASE_URL etc.
  define: Object.fromEntries(
    Object.entries(env).map(([k, v]) => [`import.meta.env.${k}`, JSON.stringify(v)]),
  ),
})
