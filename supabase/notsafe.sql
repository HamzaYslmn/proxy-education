-- Run in the Supabase SQL editor. Idempotent for a fresh DB.
-- TEACHING DEMO: `private` RLS is CORRECT (a direct read returns only your own row), but a SECURITY
-- DEFINER computed relationship leaks it through the JOIN  GET /public?select=*,private(*).  Plus an
-- RLS-disabled `logs` table and an all_notes() RPC as extra examples.

-- ⚠️ The id is now the user's auth uid (uuid), not a bigint. If you ran the old version,
--    drop the old tables first (uncomment) — this DELETES their rows:
-- drop table if exists public.private cascade;
-- drop table if exists public.public  cascade;
-- drop table if exists public.logs    cascade;

-- pg_graphql exposes a second read API at /graphql/v1 — part of the demo's attack surface.
-- create extension if not exists pg_graphql;

-- MARK: Tables — both keyed by the caller's auth uid (id = auth.uid()) and both referencing
-- auth.users. There is deliberately NO foreign key between public and private: the embed
-- GET /public?select=*,private(*) is wired up by a SECURITY DEFINER function below (the JOIN bug),
-- not a real FK — which is exactly what lets the embed bypass RLS while a direct read cannot.
create table if not exists public.public (
  id         uuid primary key default auth.uid() references auth.users(id) on delete cascade,
  created_at timestamptz not null default now(),
  data       jsonb            -- { username, registered_at }
);

create table if not exists public.private (
  id         uuid primary key default auth.uid() references auth.users(id) on delete cascade,
  created_at timestamptz not null default now(),
  data       jsonb            -- { notes }
);

-- 🚨 DELIBERATE BUG (RLS never enabled): a table created via raw SQL has RLS OFF by default — the
--    most common Supabase mistake of all. With RLS off, the anon role's default grants apply
--    directly: ANYONE can select, insert, update and DELETE every row.
create table if not exists public.logs (
  id         bigint generated always as identity primary key,
  created_at timestamptz not null default now(),
  message    text
);
insert into public.logs (message)
select 'admin: rotate the staging service key before launch'
where not exists (select 1 from public.logs);
-- (there is deliberately NO "enable row level security" on public.logs)

-- MARK: RLS
alter table public.public  enable row level security;
alter table public.private enable row level security;

-- public: world-readable profiles; you may only write your own row (id must be your uid)
drop policy if exists "public read"       on public.public;
drop policy if exists "public insert own" on public.public;
drop policy if exists "public update own" on public.public;
create policy "public read"       on public.public for select using (true);
create policy "public insert own" on public.public for insert with check (id = auth.uid());
create policy "public update own" on public.public for update using      (id = auth.uid());

-- private: writes are owner-only — and SELECT is now CORRECT too, so a DIRECT read only ever returns
-- your OWN row. As a logged-in user:  GET /rest/v1/private?id=eq.<someone-else>  → [] (nothing).
drop policy if exists "private insert own"          on public.private;
drop policy if exists "private update own"          on public.private;
drop policy if exists "private select (VULNERABLE)" on public.private;
drop policy if exists "private select own"          on public.private;
create policy "private insert own" on public.private for insert with check (id = auth.uid());
create policy "private update own" on public.private for update using      (id = auth.uid());
create policy "private select own" on public.private for select using      (id = auth.uid());

-- 🚨 THE JOIN BUG: a SECURITY DEFINER "computed relationship". PostgREST exposes this function as an
--    embeddable relationship from public → private, so  GET /public?select=*,private(*)  works — and
--    because it's SECURITY DEFINER it runs as the function OWNER and BYPASSES RLS. The embed returns
--    EVERY user's private row even though the direct SELECT policy above correctly returns only your
--    own. Direct read = safe; the JOIN through public = total leak. The proxy refuses embeds (a
--    select with parens → 422), so it can't be reached through the proxy.
--    SQLi fix: `set search_path = ''` + fully-qualified names. A SECURITY DEFINER function with a
--    mutable search_path is hijackable — an attacker who can create a `private` object in an earlier
--    schema makes the definer run THEIR code as the owner (privilege escalation). Pinning the path
--    closes that. The RLS bypass here is deliberate; the search-path injection is not.
create or replace function public.private(pub public.public)
  returns setof public.private
  language sql stable security definer
  set search_path = ''
as $$ select p.* from public.private p where p.id = pub.id $$;

-- 🚨 Same root cause, different entrypoint — a SECURITY DEFINER RPC at /rest/v1/rpc/all_notes hands
--    every note to any caller regardless of the SELECT policy. The proxy never routes /rpc.
create or replace function public.all_notes()
  returns setof public.private
  language sql stable security definer
  set search_path = ''
as $$ select * from public.private $$;

-- SECURE: make the embed (and the RPC) respect RLS again — drop the definer functions, or recreate
-- them `security invoker` so they run as the caller:
-- drop function if exists public.private(public.public);
-- drop function if exists public.all_notes();

-- SECURE `logs`: just enabling RLS denies the anon role (no policy = no access):
-- alter table public.logs enable row level security;
