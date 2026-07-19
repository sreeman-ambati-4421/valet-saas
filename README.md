# Valet Parking SaaS

Multi-tenant, WhatsApp-first valet parking management platform. Full business requirements: [`docs/valet_parking_brd.pdf`](docs/valet_parking_brd.pdf).

**Current status: Phase 1 — Foundation + thin vertical slice.** Auth, tenancy, RBAC, and a full staff-initiated valet session lifecycle (create → accept → collect → park → retrieve → deliver) are working end-to-end. WhatsApp/Twilio integration, QR codes, and full admin dashboards are later phases — see the plan history for the phase roadmap.

## Architecture

- **Frontend** (`/frontend`): React + TypeScript + Vite, PWA-enabled, Tailwind CSS, deployed on Vercel. Serves valet, venue manager, tenant admin, and platform admin — all web-based.
- **Backend** (`/backend`): Python FastAPI + SQLAlchemy (async) + Alembic. Hosted separately from the frontend (Render/Fly.io — TBD).
- **Data/Auth/Realtime**: Supabase (managed Postgres + Auth + Realtime).
- **WhatsApp**: Twilio (BSP), integrated in a later phase — the messaging layer is isolated so this can be swapped for direct Meta Cloud API later without touching core valet logic.

## Setup

### 1. Create a Supabase project

Free tier at [supabase.com](https://supabase.com). From **Settings → API** grab the Project URL, anon key, and JWT secret; from **Settings → Database** grab the connection string.

### 2. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env        # then fill in your Supabase values
alembic upgrade head
uvicorn app.main:app --reload
```

Without a `.env`, the backend defaults to a local SQLite file (`dev.db`) so it runs out of the box for exploring the API — but Supabase Auth won't have real users to log in as. Fill in `.env` for real development.

Run tests: `pytest` (uses an isolated in-memory SQLite DB, no credentials needed — includes the automated tenant-isolation and session-lifecycle suites).

Apply RLS policies (defense-in-depth tenant isolation on top of the app-level checks) via the Supabase SQL editor, or `psql $DATABASE_URL -f backend/supabase/policies.sql`, after running migrations.

### 3. Frontend

```bash
cd frontend
npm install
copy .env.example .env        # fill in Supabase URL/anon key + backend API URL
npm run dev
```

### 4. Create your first users

There's no self-serve signup yet. Create a user in Supabase Auth (dashboard or `supabase.auth.admin.createUser`), then insert a matching row in the `users` table with the same `supabase_user_id`, a `role`, and (for non-platform-admins) a `tenant_id`. Grant `venue_manager`/`valet` users venue access via `user_venue_access`.

## Repo layout

```
backend/    FastAPI app, SQLAlchemy models, Alembic migrations, tests, RLS policies
frontend/   React/TS PWA (valet, manager, tenant admin, platform admin)
docs/       Business Requirements Document (source of truth for scope)
```
