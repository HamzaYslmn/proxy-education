# proxy-education

A tiny teaching project. The **same Supabase database**, reached two ways —
**direct** (browser → Supabase) vs **proxied** (browser → FastAPI proxy → Supabase) —
so you can see, side by side, what raw PostgREST access exposes and how a thin proxy
with correct RLS shuts it down. Flip between the two with a switch in the top bar.

> ⚠️ **Educational use only.** The database ships with *deliberate* security bugs
> (a wide-open RLS policy, a `SECURITY DEFINER` function, and a table with RLS never
> enabled) so the attacks actually work. Run it against a throwaway Supabase project you
> own — never copy this schema into production.

## The lesson

`supabase/public.sql` plants three intentional mistakes. Direct PostgREST hits them; the
proxy refuses embeds, forces `id = your uid`, requires a token, exposes only a typed query
API, caps page size and rate, and only routes `public`/`private` — so `logs`, `/graphql`,
`/rpc` and the schema root are simply unreachable.

The table is ordered the way an attacker actually works — **recon → read → pivot → scale →
tamper/abuse** — which is also the order `pwn-tools` runs them in.

| #  | Attack | Direct | Proxy |
|----|--------|--------|-------|
| 1  | GraphQL scan `/graphql/v1 { __schema }` | enumerates every table | 404 (`/graphql` not routed) |
| 2  | GraphQL read `{ privateCollection … }` | leaks notes via pg_graphql | 404 |
| 3  | Schema dump `GET /rest/v1/` | OpenAPI: every table/column/FK | 404 (root not exposed) |
| 4  | Anonymous read (anon key, no login) | leaks with no auth | 401 (token required) |
| 5  | Unfiltered `private?select=data` | dumps the whole table | only your row (uid forced) |
| 6  | Cross-user `private?id=eq.<victim>` | reads the victim | your row, not theirs |
| 7  | UUID enumeration `private?id=gt.<0-uuid>` | walks every row (IDOR) | your row (`gt` ignored) |
| 8  | RLS-disabled table `logs?select=*` | reads an unprotected table | 404 (not routed) |
| 9  | JOIN/embed `public?select=*,private(*)` | leaks all users' notes | 422 (embeds refused) |
| 10 | RPC `/rpc/all_notes` (`SECURITY DEFINER`) | bypasses RLS, leaks everything | 404 (`/rpc` not routed) |
| 11 | Filter ops `or=`, `like=` | full PostgREST operator surface | 422 (typed params only) |
| 12 | Oversized `limit=100000` | one-shot table scrape | 422 (capped at 100) |
| 13 | Count leak (`Prefer: count=exact`) | whole-table row count | only your count (id forced) |
| 14 | Mass assignment (forge `created_at`) | any real column is writable | 422 (body is `data`-only) |
| 15 | Anon `DELETE` on `logs` | anyone destroys the RLS-off table | 404 (not routed) |
| 16 | 25 rapid reads | no app cap | 429 after 10/min |
| 17 | Storage bucket list `GET /storage/v1/bucket` | Storage API reachable | 404 (not routed) |
| 18 | Storage object list `POST /storage/v1/object/list/<bucket>` | walks a bucket's files if SELECT RLS is loose | 404 (not routed) |
| 19 | Edge `POST /functions/v1/<fn>` | Functions gateway reachable | 404 (not routed) |
| 20 | Realtime `WSS /realtime/v1` | live table-change stream | not supported (proxy is HTTP-only) |
| 21 | Auth config `GET /auth/v1/settings` | leaks signup / autoconfirm / OAuth providers | forwarded (Supabase config) |
| 22 | Anonymous sign-in `POST /auth/v1/signup {}` | free authenticated session if enabled | forwarded (Supabase config) |
| 23 | OAuth `authorize?redirect_to=evil` | open redirect if not allowlisted | forwarded (Supabase config) |

## Why these are dangerous, and how attackers exploit them

With direct access the **publishable (anon) key is public** — it ships in the browser, so
every visitor already has it. That makes **Row-Level Security the *only* wall** between an
attacker and your data. One loose policy, one table with RLS left off, one `SECURITY DEFINER`
function, or one forgotten endpoint exposes everything. Here's how someone turns "I have the
anon key" into "I have every user's data," in the order they'd try it.

**Recon — the API maps itself.** PostgREST and pg_graphql are *self-describing*: `GET /rest/v1/`
returns an OpenAPI document and `/graphql/v1`'s `__schema` returns the full GraphQL schema —
every table, column, type and foreign key. The attacker never has to guess blind, and even when
introspection is locked down PostgREST's **200-vs-404** confirms a guessed table name a request at
a time. GraphQL is the sneaky surface: it's **on by default and easy
to forget**, so teams harden REST and never notice the same data is reachable at `/graphql/v1`.

**Read — RLS is doing all the work.** Reading is one request. With just the anon key (no login)
an attacker hits `private?select=data`; if any SELECT policy is too loose, the whole table
returns. `id=eq.<victim>` targets one person, and `id=gt.<zero-uuid>` **walks every row by id
range** — classic IDOR, no victim list needed. Worst of all is a table with **RLS never enabled**
(`logs`): tables made via raw SQL have RLS *off* by default — the single most common Supabase
mistake — and with it off the anon role's default grants apply directly, so anyone reads it.
These work because **the client chooses the filter and the database is the only gate**.

**Pivot — even when the policy is right.** This is the nasty one: `private`'s SELECT policy is
*correct* — a direct read returns only your own row. But **resource embedding**
(`public?select=*,private(*)`) reads `private` *through* `public` via a **`SECURITY DEFINER`
computed relationship**, a function PostgREST exposes as the embed. It runs as its owner and
**bypasses RLS entirely**, so the JOIN leaks every user's row while the direct read stays locked.
The same `SECURITY DEFINER` trap shows up as an RPC (`/rpc/all_notes`) — one exposed helper leaks
everything regardless of policy. Both are common real-world Supabase breaches; the lesson is that a
correct RLS policy is *not* enough if a definer function quietly re-exposes the data.

**Scale — one row becomes the whole table.** PostgREST exposes its **full operator set** (`or`,
`like`, `not`, `in`, full-text). Even against correct RLS these power **boolean-oracle
enumeration** (extract hidden values character by character) and `like '%…%'` table-scan DoS.
`limit=100000` scrapes everything in one shot, and `Prefer: count=exact` leaks the **exact row
count** — how many users you have, how big the breach is worth — without reading a single row.

**Tamper & abuse.** Writes land in **any real column**, not just the ones the UI uses —
`created_at`, an internal `role`/`is_admin`, a foreign key (mass assignment → privilege
escalation). And when a table has **RLS off**, the anon role can `INSERT`/`UPDATE`/**`DELETE`**
it freely — an attacker doesn't just read your data, they can wipe it. With **no application
rate limit**, every attack above runs at full speed — scraping, enumeration, credential
stuffing — bounded only by Postgres.

**Beyond PostgREST — the other Supabase APIs.** A project is more than its tables. **Storage**
(`/storage/v1`) lets the anon key enumerate buckets and probe object permissions; **Edge Functions**
(`/functions/v1`) expose a public gateway to invoke; **Realtime** (`wss /realtime/v1`) streams every
table change live, so loose RLS leaks other users' writes in real time; and **OAuth** authorize
chains (`/auth/v1/authorize?redirect_to=…`) become token theft if `redirect_to` isn't allowlisted.
Attackers probe all of these, not just the REST API.

**How the proxy stops all of it.** It never trusts the caller: a **narrow, typed API** (only the
columns and filters the app needs), **`id = your uid` forced server-side** on every private
read/write, **embeds and unknown params rejected** (422), a **real token required** (401), **page
size and rate capped**, and a **tiny routed surface** — only `public`/`private` plus the auth
endpoints login needs, so `logs`, `/graphql`, `/rpc`, `/storage`, `/functions`, `/realtime` and the
schema root all return 404. The one it can't fix alone is **OAuth redirect**: it forwards `/auth`,
so redirect safety stays a Supabase-dashboard allowlist (a stricter proxy could allowlist the auth
paths it forwards). Same database, same RLS — the difference is a gateway that assumes the caller is
hostile.

Writes to the *correctly-secured* tables aren't the leak — `public`/`private` insert/update
policies are owner-only. The exposure is the broken SELECT policy, the `SECURITY DEFINER`
function, and the RLS-off `logs` table.

## Real-world tooling

live checks; Realtime is noted rather than connected (it's a WebSocket, and the proxy is HTTP-only).
The proxy's answer to all of them is the same: don't route what the app doesn't need.

## Run it

1. Create a throwaway Supabase project; paste `supabase/public.sql` into the SQL editor. Turn **email confirmation OFF** (Auth → Providers → Email) so the demo can register users.
2. **Backend:** set `SUPABASE_SERVICE_KEY` in `backend/src/.env`, then `cd backend && ./run.sh` (proxy on :8001).
3. **Frontend:** `cd frontend && pnpm i && pnpm dev`, then toggle **direct / proxied** in the top bar.
4. **See the attacks:** `cd pwn-tools && uv run python main.py test` (auto-registers 3 demo users, red = direct, green = proxy). Or `python main.py recon <site-url>` to extract a site's Supabase URL, keys and tables.
