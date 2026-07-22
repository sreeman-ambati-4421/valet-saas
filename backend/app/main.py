from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, invites, me, qrcodes, sessions, staff, tenants, venues, whatsapp_webhook
from app.core.config import settings

app = FastAPI(title="Valet Parking SaaS API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(me.router)
app.include_router(tenants.router)
app.include_router(venues.router)
app.include_router(sessions.router)
app.include_router(staff.router)
app.include_router(qrcodes.router)
app.include_router(invites.router)
app.include_router(whatsapp_webhook.router)
