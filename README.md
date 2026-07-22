# Valet Parking SaaS

Multi-tenant, WhatsApp-first valet parking management platform. Full business requirements: [`docs/valet_parking_brd.pdf`](docs/valet_parking_brd.pdf).

**Current status: Phase 1 — Foundation + thin vertical slice.** Auth, tenancy, RBAC, WhatsApp/Twilio integration (QR scan → reg. number capture → status updates), and a full session lifecycle (request → accept → park → retrieval requested → retrieving → ready → complete) are working end-to-end.

**Roles.** There is no driver-facing role: valet drivers never touch the app. They're coordinated verbally by whoever's at the desk.
- `saas_owner` — platform operator; onboards tenants and their business owner.
- `business_owner` — owns a tenant (hotel/restaurant/venue group); manages venues, QR codes, and desk staff across all their venues.
- `valet_desk` — the person at the valet desk; accepts guest requests, dispatches drivers verbally, and reports status back over WhatsApp (park confirmed / retrieving / ready).

## Architecture

- **Frontend** (`/frontend`): React + TypeScript + Vite, PWA-enabled, Tailwind CSS, deployed on Vercel. Serves the SaaS owner, business owner, and valet desk dashboards — all web-based.
- **Backend** (`/backend`): Python FastAPI + SQLAlchemy (async) + Alembic. Hosted separately from the frontend (Render/Fly.io — TBD).
- **Data/Auth/Realtime**: Supabase (managed Postgres + Auth + Realtime).
- **WhatsApp**: Twilio (BSP), for both guest conversations and staff sign-in/notifications — the messaging layer is isolated so this can be swapped for direct Meta Cloud API later without touching core valet logic.

## Setup

### 1. Create a Supabase project

Free tier at [supabase.com](https://supabase.com). From **Settings → API** grab the Project URL, anon key, and JWT secret; from **Settings → Database** grab the connection string.

**Enable phone auth (required — there is no email/password login):** In **Authentication → Providers**, enable the **Phone** provider and set the SMS provider to **Twilio** using the same Account SID/Auth Token/Verify Service as your Twilio setup below, with the **channel set to WhatsApp** (Twilio Verify supports SMS, call, and WhatsApp as delivery channels — this project uses WhatsApp so staff never receive a plain SMS). You'll need a Twilio Verify Service (separate from the WhatsApp Sender used for guest messaging) — create one in the Twilio console.

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

There's no self-serve signup. Login is WhatsApp-OTP based (phone number → code sent via WhatsApp → verified in-browser, no password). To bootstrap your first `saas_owner` (every other account is created through the app's own invite flow after that):

1. In Supabase Auth (dashboard or `supabase.auth.admin.createUser`), create a user with `phone` set to your WhatsApp number and `phone_confirm: true`.
2. Insert a matching row in the `users` table with the same `supabase_user_id`, that `phone_number`, `role = 'saas_owner'`, `tenant_id = NULL`, `is_active = true`.
3. Sign in at `/login` with that phone number.

From there, a `saas_owner` invites `business_owner`s, who invite `valet_desk` staff — both flows create a phone-confirmed Supabase account and just send a WhatsApp notification (no link to click) telling the recipient to sign in with their number.

## Repo layout

```
backend/    FastAPI app, SQLAlchemy models, Alembic migrations, tests, RLS policies
frontend/   React/TS PWA (valet, manager, tenant admin, platform admin)
docs/       Business Requirements Document (source of truth for scope)
```
