# Valet Parking SaaS

Multi-tenant, WhatsApp-first valet parking management platform. Full business requirements: [`docs/valet_parking_brd.pdf`](docs/valet_parking_brd.pdf).

**Current status: Phase 1 — Foundation + thin vertical slice.** Auth, tenancy, RBAC, WhatsApp/Twilio integration (tag scan → status updates), and a full session lifecycle (request → accept → park → retrieval requested → retrieving → ready → complete) are working end-to-end.

**Physical key tags, not a fixed venue QR.** A venue pre-generates a pool of QR-coded tags, printed onto plastic key fobs. Guest scans a tag on arrival (WhatsApp opens, request created instantly — no reg. number question), the driver keeps that same tag attached to the vehicle's keys, and it's released back to the available pool the moment the session completes. Registration number is captured from the driver at the **Mark Parked** step instead, since the tag — not the reg. number — is what links guest to vehicle now.

**Roles.** There is no driver-facing role: valet drivers never touch the app. They're coordinated verbally by whoever's at the desk.
- `saas_owner` — platform operator; onboards tenants and their business owner.
- `business_owner` — owns a tenant (hotel/restaurant/venue group); manages venues, key tags, and desk staff across all their venues.
- `valet_desk` — the person at the valet desk; accepts guest requests, dispatches drivers verbally, and reports status back over WhatsApp (park confirmed / retrieving / ready). New requests also notify every desk person with access to that venue over WhatsApp, with a short code (`ACCEPT-<code>`) they can reply with to claim it remotely — same underlying atomic accept as the dashboard button, so only one of them wins if both try.

## Architecture

- **Frontend** (`/frontend`): React + TypeScript + Vite, PWA-enabled, Tailwind CSS, deployed on Vercel. Serves the SaaS owner, business owner, and valet desk dashboards — all web-based.
- **Backend** (`/backend`): Python FastAPI + SQLAlchemy (async) + Alembic. Hosted separately from the frontend (Render/Fly.io — TBD).
- **Data/Auth/Realtime**: Supabase (managed Postgres + Auth + Realtime).
- **WhatsApp**: Twilio (BSP), for guest conversations and staff invite links — the messaging layer is isolated so this can be swapped for direct Meta Cloud API later without touching core valet logic. Staff authenticate with a phone number + password (set via the invite link); there is no OTP/Twilio Verify involved in login at all.

## Setup

### 1. Create a Supabase project

Free tier at [supabase.com](https://supabase.com). From **Settings → API** grab the Project URL, anon key, and JWT secret; from **Settings → Database** grab the connection string.

**Enable phone auth (required — there is no email-based login):** In **Authentication → Providers**, enable the **Phone** provider. No SMS/OTP provider needs to be configured — this project never sends a Supabase-mediated OTP; accounts are created phone-confirmed but password-less, and get a real password only once their invite link is accepted (see below). Login is then plain `signInWithPassword({ phone, password })`.

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

### 4. Create your first user

There's no self-serve signup. Login is phone number + password. To bootstrap your first `saas_owner` (every other account is created through the app's own invite flow after that, with a real password of their own choosing):

1. In Supabase Auth (dashboard or `supabase.auth.admin.createUser`), create a user with `phone` set to your WhatsApp number, a `password` of your choosing, and `phone_confirm: true`.
2. Insert a matching row in the `users` table with the same `supabase_user_id`, that `phone_number`, `role = 'saas_owner'`, `tenant_id = NULL`, `is_active = true`.
3. Sign in at `/login` with that phone number and password.

From there, a `saas_owner` invites `business_owner`s, who invite `valet_desk` staff. Both flows create a phone-confirmed but password-less Supabase account and send a WhatsApp message containing a one-time `/accept-invite` link (signed with the backend's own `INVITE_TOKEN_SECRET`, valid for 7 days). The recipient sets their password there, then signs in normally at `/login`.

## Repo layout

```
backend/    FastAPI app, SQLAlchemy models, Alembic migrations, tests, RLS policies
frontend/   React/TS PWA (valet desk, business owner, SaaS owner)
docs/       Business Requirements Document (source of truth for scope)
```
