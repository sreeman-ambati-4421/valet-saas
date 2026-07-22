import io
import secrets
import urllib.parse

import qrcode
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.deps import get_current_user, require_role, require_venue_access
from app.models.parking import QRCode, TagStatus
from app.models.tenant import Venue
from app.models.user import User, UserRole
from app.schemas.qrcode import QRCodeCreate, QRCodeOut

router = APIRouter(tags=["qrcodes"])


async def _generate_unique_token(db: AsyncSession) -> str:
    """A short 6-character hex code -- readable in the pre-filled WhatsApp
    message ("tag A1B3F0") instead of a long opaque secret, while still
    unique enough that collisions across a venue's tag pool are
    vanishingly unlikely (16.7M possible values)."""
    for _ in range(10):
        candidate = secrets.token_hex(3).upper()
        existing = await db.execute(select(QRCode.id).where(QRCode.token == candidate))
        if existing.scalar_one_or_none() is None:
            return candidate
    raise RuntimeError("Could not generate a unique tag code after 10 attempts")


def _wa_link(token: str, venue_name: str) -> str:
    number_digits = settings.twilio_whatsapp_number.replace("whatsapp:", "").replace("+", "")
    text = urllib.parse.quote(f"👋 Hi {venue_name}! My car needs to be parked -- tag {token}.")
    return f"https://wa.me/{number_digits}?text={text}"


def _to_out(qr: QRCode, venue_name: str) -> QRCodeOut:
    out = QRCodeOut.model_validate(qr)
    out.wa_link = _wa_link(qr.token, venue_name)
    return out


@router.post("/venues/{venue_id}/qr-codes", response_model=list[QRCodeOut], status_code=201)
async def create_qr_codes(
    venue_id: str,
    payload: QRCodeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.BUSINESS_OWNER, UserRole.SAAS_OWNER)),
) -> list[QRCodeOut]:
    """Bulk-generates `count` physical key tags for a venue -- printed with
    their QR + label, attached to vehicle keys one at a time as guests
    arrive. Existing tag count for the venue determines where numbering
    continues from, so repeated calls keep sequential labels."""
    await require_venue_access(venue_id, current_user, db)
    venue = await db.get(Venue, venue_id)

    existing_count = await db.scalar(select(func.count()).select_from(QRCode).where(QRCode.venue_id == venue_id))
    new_tags = []
    for i in range(1, payload.count + 1):
        token = await _generate_unique_token(db)
        qr = QRCode(venue_id=venue_id, token=token, label=f"Tag {existing_count + i}")
        db.add(qr)
        new_tags.append(qr)
    await db.commit()
    for qr in new_tags:
        await db.refresh(qr)
    return [_to_out(qr, venue.name) for qr in new_tags]


@router.get("/venues/{venue_id}/qr-codes", response_model=list[QRCodeOut])
async def list_qr_codes(
    venue_id: str,
    status_filter: TagStatus | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[QRCodeOut]:
    await require_venue_access(venue_id, current_user, db)
    venue = await db.get(Venue, venue_id)
    query = select(QRCode).where(QRCode.venue_id == venue_id, QRCode.is_active.is_(True))
    if status_filter is not None:
        query = query.where(QRCode.status == status_filter)
    result = await db.execute(query.order_by(QRCode.label))
    return [_to_out(qr, venue.name) for qr in result.scalars().all()]


@router.get("/qr-codes/{qr_code_id}/image")
async def get_qr_code_image(qr_code_id: str, db: AsyncSession = Depends(get_db)) -> Response:
    # Deliberately public/unauthenticated -- it's just a PNG meant to be
    # printed and scanned by guests who have no account.
    qr = await db.get(QRCode, qr_code_id)
    if qr is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "QR code not found")
    venue = await db.get(Venue, qr.venue_id)

    img = qrcode.make(_wa_link(qr.token, venue.name if venue else "our valet service"))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Response(content=buf.getvalue(), media_type="image/png")
