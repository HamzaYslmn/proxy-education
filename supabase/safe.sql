-- Run in the Supabase SQL editor. The SAFE counterpart to public.sql: no leaks.
-- Every row is keyed by the caller's auth uid, RLS is ON, and all four operations are
-- owner-only (id = auth.uid()). No world-readable policy, no SECURITY DEFINER functions,
-- no RLS-off tables. Direct PostgREST access can only ever touch your own rows.

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

alter table public.public  enable row level security;
alter table public.private enable row level security;

-- One policy per table covering SELECT/INSERT/UPDATE/DELETE: you only ever see or change
-- your own row. `using` gates read/update/delete; `with check` gates insert/update writes.
do $$
declare t text;
begin
  foreach t in array array['public', 'private'] loop
    execute format('drop policy if exists "own rows" on public.%I', t);
    execute format(
      'create policy "own rows" on public.%I for all
         using (id = auth.uid()) with check (id = auth.uid())', t);
  end loop;
end $$;
