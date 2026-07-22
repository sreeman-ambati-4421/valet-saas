-- Row Level Security policies: defense in depth on top of the FastAPI-level
-- RBAC checks in app/deps.py. If the app layer ever has a bug, these are the
-- second independent barrier stopping a query from crossing tenant boundaries.
--
-- Apply this AFTER running Alembic migrations against your Supabase project's
-- Postgres database (e.g. via the Supabase SQL editor, or `psql $DATABASE_URL -f policies.sql`).
--
-- Assumes: auth.uid() (Supabase's authenticated user id, a uuid) matches the
-- `users.supabase_user_id` column populated when a user is provisioned.

-- Helper: resolve the calling Supabase auth user to this app's internal user row.
create or replace function app_current_user_tenant_id()
returns text
language sql
security definer
stable
as $$
  select tenant_id from users where supabase_user_id = auth.uid()::text
$$;

create or replace function app_current_user_role()
returns text
language sql
security definer
stable
as $$
  select role from users where supabase_user_id = auth.uid()::text
$$;

-- ── venues ──────────────────────────────────────────────────────────────
alter table venues enable row level security;

create policy venues_platform_admin_all on venues
  for all
  using (app_current_user_role() = 'saas_owner');

create policy venues_tenant_isolation on venues
  for all
  using (tenant_id = app_current_user_tenant_id());

-- ── users ───────────────────────────────────────────────────────────────
alter table users enable row level security;

create policy users_platform_admin_all on users
  for all
  using (app_current_user_role() = 'saas_owner');

create policy users_tenant_isolation on users
  for select
  using (tenant_id = app_current_user_tenant_id());

create policy users_self_read on users
  for select
  using (supabase_user_id = auth.uid()::text);

-- ── valet_sessions ──────────────────────────────────────────────────────
alter table valet_sessions enable row level security;

create policy sessions_platform_admin_all on valet_sessions
  for all
  using (app_current_user_role() = 'saas_owner');

create policy sessions_tenant_isolation on valet_sessions
  for all
  using (tenant_id = app_current_user_tenant_id());

-- ── session_events ──────────────────────────────────────────────────────
alter table session_events enable row level security;

create policy session_events_platform_admin_all on session_events
  for all
  using (app_current_user_role() = 'saas_owner');

create policy session_events_tenant_isolation on session_events
  for select
  using (
    session_id in (
      select id from valet_sessions where tenant_id = app_current_user_tenant_id()
    )
  );

-- Note: the FastAPI backend connects using the Supabase service role key
-- (which bypasses RLS) for normal application queries -- app-level RBAC in
-- app/deps.py is the primary enforcement path. These policies exist as a
-- backstop if the anon/authenticated key is ever used directly (e.g. future
-- direct-from-frontend Supabase Realtime subscriptions), and as a safety net
-- against app-layer bugs.
