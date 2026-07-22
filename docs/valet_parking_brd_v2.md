# Business Requirements Document — v2

## WhatsApp-Based Valet Parking Management SaaS Platform

Version 2.0 | Reflects the implemented system as of this document's writing.
Supersedes `valet_parking_brd.pdf` (v1.0, July 2026), which described the
original planning scope. This version documents what was actually built,
where it diverged from the original plan, and why.

---

## 1. Executive Summary

A multi-tenant, WhatsApp-first valet parking management platform. Guests
scan a pre-printed physical key tag on arrival, request their car back over
WhatsApp, and staff run the entire operation — from accepting a request to
handing the car back — through a web dashboard. There is no native app for
guests or staff, and no valet-driver-facing login: drivers are coordinated
verbally by whoever is staffing the desk.

The platform is one centrally operated service. Each subscribing business
(a "tenant") onboards its own WhatsApp Business number and manages one or
more venues under a single account.

---

## 2. Roles

The system has exactly three roles. There is deliberately no fourth,
driver-facing role — valet drivers physically move vehicles but never sign
in anywhere; they're directed by voice/radio by the person at the desk.

| Role | Scope | Responsibilities |
|---|---|---|
| **SaaS Owner** | Platform-wide | Onboards tenants; invites each tenant's first Business Owner. Not scoped to any single tenant. |
| **Business Owner** | One tenant, all its venues | Creates venues, generates key tags, invites Valet Desk staff, monitors all sessions across their venues (read-only oversight — cannot act on individual sessions from this view). |
| **Valet Desk** | One or more venues within a tenant | The only role that operates the live queue: accepts requests, marks vehicles parked, retrieving, ready, and complete. |

A **Business Owner** in this system combines what the original plan called
"Tenant Admin" (account-level, multi-venue) and "Venue Manager"
(venue-level operations) into one role — there was no reason to keep them
separate once the platform reached three roles total.

---

## 3. Authentication

**Phone number + password. No email, anywhere, at any point.**

- Login: `phone number + password`, verified against Supabase Auth. No OTP,
  no magic link involvement in login at all.
- **Bootstrapping the first SaaS Owner** is a one-time manual step: create
  the Supabase Auth user directly (phone + a real password you choose),
  then insert the matching `users` row with `role = 'saas_owner'`.
- **Every other account is invited**, never self-registered:
  - A SaaS Owner invites a Business Owner. A Business Owner invites Valet
    Desk staff.
  - The invited account is created in Supabase **phone-confirmed but
    password-less** — an account can validly exist with no password set
    yet.
  - The recipient gets a WhatsApp message containing a one-time
    `/accept-invite` link. The link carries a token **signed by our own
    backend** (not a Supabase-issued one) — Supabase has no "magic link"
    concept for phone-identified accounts, so this had to be built rather
    than reused.
  - Because the token is only *evaluated* when the recipient submits a
    password (a `POST`), simply viewing the link does nothing. This makes
    the design naturally immune to WhatsApp's link-preview bot prematurely
    consuming a single-use token — a problem that would exist with a
    Supabase-issued link, but doesn't here.
  - Once the password is set, the account activates and the recipient
    signs in normally at `/login`.

**Why not WhatsApp OTP login?** It was tried first, but an OTP-based
channel requires an approved WhatsApp Business Sender and adds a
verification-provider dependency just for login. That was passed over in
favor of the simpler, fully-controlled password + invite-link design
above.

---

## 4. Key Tags (replaces the original "fixed venue QR" concept)

The original plan (v1) called for a single, permanent QR code per venue
(or per entrance) that every guest scans, followed by the guest typing
their registration number over WhatsApp. **This was replaced** with a pool
of individually tracked physical key tags, closer to how valet operations
actually run in practice with a physical token per vehicle.

- A Business Owner bulk-generates a pool of tags per venue (e.g. 20 at
  once) from the dashboard — each gets a unique QR code and a
  human-readable label ("Tag 1", "Tag 2", ...), meant to be printed onto a
  physical plastic key fob.
- Each tag has a status: `available` or `in_use`. A tag can only be
  attached to one active session at a time (enforced with the same
  atomic-update pattern used for job acceptance — see §7).
- **Guest arrival**: guest scans an available tag → WhatsApp opens with a
  pre-filled message → guest sends it → a session is created **immediately**,
  the tag flips to `in_use`. No registration-number question at this point.
- **Driver** keeps that same physical tag attached to the vehicle's keys
  for the duration of the session.
- **Registration number** is now captured from the driver at the **Mark
  Parked** step in the app instead — since the tag, not the reg. number, is
  what links guest to vehicle now, and the driver is standing at the car
  when they'd know it anyway.
- **Tag release**: the moment a session reaches `COMPLETED` or `CANCELLED`,
  its tag automatically flips back to `available`, ready for the next
  guest — no manual "release" step.
- **Guests without WhatsApp**: a Valet Desk person can still create a
  session manually from the dashboard. The backend auto-assigns any
  available tag for the venue (no tag picker needed — one available tag is
  as good as another).

---

## 5. Session Lifecycle

```
REQUESTED → ACCEPTED → PARKED → RETRIEVAL_REQUESTED → RETRIEVING → READY → COMPLETED
                                                                              ↘
                                                            CANCELLED (from any state before READY)
```

| State | Reached by | Guest WhatsApp message sent? |
|---|---|---|
| `REQUESTED` | Guest scans an available tag (or staff creates manually) | Welcome / request-received message |
| `ACCEPTED` | A Valet Desk person taps "Accept" (app or WhatsApp reply — see §6) | — |
| `PARKED` | Desk person taps "Mark Parked," enters registration number | "Your vehicle has been parked safely..." |
| `RETRIEVAL_REQUESTED` | Guest sends "car"/"retrieve"/"pickup" over WhatsApp (WhatsApp-originated sessions) **or** desk taps "Request Retrieval" (staff-created sessions only — see below) | "Got it! We're bringing your car around now." |
| `RETRIEVING` | Desk person taps "Mark Retrieving" after verbally dispatching a driver | "Your vehicle is being retrieved." |
| `READY` | Desk person taps "Mark Ready" once the car is back | "Your car is ready for pickup!" |
| `COMPLETED` | Desk person taps "Complete" once the guest has left with their car | — |
| `CANCELLED` | Not currently exposed via any endpoint; reachable in the data model, not yet wired to a UI action | — |

**Important asymmetry, by design**: sessions the guest started themselves
over WhatsApp can **only** have retrieval requested by the guest's own "car"
message — staff cannot trigger it on their behalf for these. Sessions
created manually by staff (for a guest without WhatsApp) keep a manual
"Request Retrieval" fallback button, since there's no guest conversation to
drive it. This is tracked with a `created_via_whatsapp` flag on the
session.

Every accept/park/retrieve/ready/complete action is only permitted for the
specific Valet Desk person who accepted that job, or a Business Owner as an
override — enforced server-side, not just hidden in the UI.

---

## 6. WhatsApp Integration

### 6.1 Guest conversation

- Scan → instant session creation, no follow-up question.
- Guest can message "car" (or "retrieve"/"pickup") any time the vehicle is
  `PARKED` to request retrieval.
- Any other message returns the session's current status in plain
  language.

### 6.2 Staff notifications and remote accept

- Every new `REQUESTED` session notifies **every Valet Desk person with
  access to that venue** over WhatsApp, including a short code:
  *"New request: Tag 007. Reply ACCEPT-4F2A91 to claim it, or open the
  app."*
- A desk person can reply `ACCEPT-<code>` directly from WhatsApp to claim
  the job remotely (e.g. if they're away from the desk) — this runs
  through the **same atomic accept logic** as the dashboard button, so a
  WhatsApp reply racing an app tap resolves exactly like two app taps
  would (first one in wins, the other gets a clear rejection).
- This required the webhook to check, before assuming any inbound message
  is a guest: *is this sender's number a known, active staff phone number?*
  If so, it's routed to a separate staff-command handler instead. Only
  `ACCEPT-<code>` is supported remotely — every later step requires
  physically being at the vehicle, so there's nothing to gain from
  supporting those over WhatsApp too.

### 6.3 Provider: Meta WhatsApp Cloud API (direct integration)

The backend talks directly to Meta's WhatsApp Cloud API (Graph API) — no
Business Solution Provider in between. Inbound messages arrive at a single
webhook (`GET`/`POST /webhooks/whatsapp`); outbound messages go straight to
`https://graph.facebook.com/{version}/{phone_number_id}/messages`.

Setup, once, in Meta Business Manager:

1. **Meta Business Manager**: verify the business (name, address, and
   sometimes supporting documents).
2. **WhatsApp Business Account (WABA)**: created under that Business
   Manager, with a dedicated phone number that must never have been used
   on the regular WhatsApp/WhatsApp Business app before.
3. **System User + permanent access token**: generated in Business
   Manager, granted `whatsapp_business_messaging` — this is what the
   backend authenticates with (`WHATSAPP_ACCESS_TOKEN`), not a 24-hour
   test token.
4. **Webhook configuration**: point Meta's App dashboard at
   `https://<backend>/webhooks/whatsapp`, with a verify token
   (`WHATSAPP_VERIFY_TOKEN`) matching what the backend expects, and
   subscribe to the `messages` field.
5. **Display name approval** by Meta.

Any WhatsApp user can be messaged directly — there is no sandbox join-code
step at any stage. In exchange, **message templates are mandatory** for
anything the business sends outside an open 24-hour conversation window
(i.e., anything the business sends *before* the recipient has messaged
first, or long after their last message). Concretely, this affects:

| Message | Business- or guest/staff-initiated? | Template needed in production? |
|---|---|---|
| Guest scan replies, status replies, retrieval ack | Reply to guest's own inbound message | No — within window |
| Staff invite ("you've been invited...") | Business-initiated, recipient has never messaged | **Yes** |
| "New request, reply ACCEPT-..." | Business-initiated; staff may not have an open window | **Yes** |
| PARKED / RETRIEVING / READY status updates | Triggered by staff action, not a direct reply | Usually fine within window (typical valet turnaround is well under 24h); a template is the safer long-term choice if long-duration parking is expected |
| Accept-confirmation, "wasn't found," "already claimed," etc. | Reply to staff's own inbound message | No — within window |

Practically: **2 templates required, 1 recommended** —
1. Staff invite (Utility category)
2. New-request notification to desk staff (Utility category)
3. *(Recommended)* A generic, parameterized guest status-update template,
   to guarantee delivery even in the rare case a vehicle sits long enough
   for the guest's window to close.

Meta's per-WABA template cap is not a practical constraint at this scale
(historically far higher than a business like this would ever need) — this
is a design question of "how many do we need," not "how many are we
allowed."

---

## 7. Core Data Model

| Entity | Notes |
|---|---|
| **Tenant** | A subscribing business. `saas_owner` is not scoped to one. |
| **Venue** | Belongs to a tenant. A tenant may have several. |
| **User** | `saas_owner` \| `business_owner` \| `valet_desk`. Identified by `phone_number`, not email. |
| **UserVenueAccess** | Grants a `valet_desk` user access to specific venues. `business_owner` implicitly has access to every venue in their own tenant — no explicit grant rows needed for them. |
| **Guest** | Identified by WhatsApp number. Not tenant-scoped — the same person may valet at unrelated venues over time. |
| **Vehicle** | Just a normalized registration number. (`make`/`model`/`color` fields existed in the original plan but were never wired to any code path, and have been removed.) |
| **QRCode** (a physical key tag) | `venue_id`, `token` (the QR's secret), `label` (human-readable, e.g. "Tag 7"), `status` (`available`/`in_use`), `is_active` (soft-retire a lost/damaged tag). |
| **ValetSession** | The core lifecycle record — see §5. `vehicle_id` is nullable (unknown until parked). `qr_code_id` links to the tag in use. `created_via_whatsapp` drives the retrieval-request asymmetry in §5. |
| **SessionEvent** | Full timestamped audit trail of every state transition, with the acting user (or null for guest/system-triggered ones). |

**Removed from the original plan** (declared in early scaffolding, never
actually used by any endpoint or service):
- `ParkingZone` / `ParkingSlot` and the corresponding fields on
  `ValetSession` — no zone/slot management was ever built; the physical
  tag now serves the location-tracking purpose these were meant for.
- `WhatsAppAccount` — the Meta Cloud API credentials are a single global
  account via environment variables, not per-tenant database rows.
- `Subscription` — billing/plan tracking was marked lowest priority in the
  original plan and never built.

---

## 8. Non-Functional Requirements (unchanged from v1 except where noted)

- **Security**: HTTPS, RBAC enforced server-side (never trust a
  client-supplied tenant/venue ID), Meta webhook signature verification
  (`X-Hub-Signature-256`, HMAC-SHA256 keyed with the App Secret), tenant
  isolation backed by Postgres RLS as defense-in-depth.
- **Auditability**: every session state transition is recorded with actor
  and timestamp.
- **Concurrency safety**: job acceptance and tag claiming both use atomic
  conditional database updates, not read-then-write — proven under
  concurrent load via automated tests, including a WhatsApp-reply-vs-app-tap
  race.
- **Mobile usability**: the Valet Desk dashboard is the one interface staff
  use continuously; it must work on ordinary mobile browsers.

---

## 9. Recommendation / Current Status

The pilot-scope thin vertical slice is complete and working end-to-end:
authentication and invites, tenancy and RBAC, key-tag generation and
lifecycle, the full guest WhatsApp conversation, the full staff session
lifecycle (including remote accept-by-WhatsApp-reply), and audit history.

**Before commercial pilot rollout**, the one remaining gap is completing
Meta Business verification and getting the 2–3 message templates in §6.3
approved. No other architectural changes are anticipated for this.

---

## 10. Out of Scope (unchanged from v1)

Native iOS/Android apps, AI chatbot, license-plate recognition, GPS
tracking, parking-zone/slot optimization, payment gateway, and enterprise
integrations remain excluded from the current build.
