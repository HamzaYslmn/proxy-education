# pwn-tools

A small CLI that demonstrates Supabase misconfigurations the way real pentest tools
(`supabase-pwn`, `supabomb`, `supashield`) do — and proves the project's proxy blocks every one.

> ⚠️ **Educational / authorized testing only.** `test` targets the bundled demo project; only
> point `recon` at sites you own or are authorized to assess.

## Usage

```bash
# Interactive menu — pick actions by number (easiest):
uv run python main.py
#   1) Recon  2) Show check list  3) Run ALL  4) Run a selection (#, range 5-9, or phase)
#   5) Step through one-by-one  6) Settings  0) Quit

# Or run directly:
uv run python main.py recon https://your-app.example.com   # extract URL, keys, tables
uv run python main.py test                                 # recon the frontend, then all checks
uv run python main.py test --frontend http://localhost:5173/ --proxy http://localhost:8001/api/db
```

`test` reads the Supabase URL + anon key out of the frontend (no hardcoded creds), so it needs the
**frontend** running, the backend **proxy** on `:8001`, `supabase/public.sql` applied, and email
confirmation **off** (it auto-registers 3 demo users).

## Layout

- `main.py` — interactive menu + CLI (`recon`, `test`).
- `recon.py` — fetch HTML+JS and **decode the JWTs**: classifies each key by privilege
  (anon/`sb_publishable_` vs leaked `sb_secret_`/`service_role` vs `sbp_` Management-API PAT),
  reconstructs the project URL from the JWT `ref`, and extracts `.from()` tables, `.rpc()`
  functions, `.storage.from()` buckets and `.invoke()` edge functions — which feed the attack phase.
- `core.py` — `Ctx` (target + recon'd buckets/functions/rpcs + HTTP helpers) and shared formatting.
- `auth.py` — registers the 3 demo users.
- `checks/` — **one file per issue** (23 of them), each a `run(ctx)` printing DIRECT vs PROXY.
  `checks/__init__.py` lists them in attacker-chain order: recon → read → pivot → scale → tamper →
  surface → auth. `surface` covers Storage (bucket + object list), Edge Functions and Realtime
  (noted, not connected — WebSocket, proxy is HTTP-only); `auth` covers GoTrue settings disclosure,
  anonymous sign-in and OAuth redirect — all *forwarded* by the proxy (Supabase-config issues).

To add a check: drop a `checks/my_check.py` with `PHASE`, `TITLE`, `run(ctx)`, and add it to
`ALL` in `checks/__init__.py`.

See the project root `README.md` for what each issue is and why it's dangerous.
