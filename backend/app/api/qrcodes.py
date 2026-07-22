import io
import secrets
import urllib.parse

import qrcode
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.deps import get_current_user, require_role, require_venue_access
from app.models.parking import QRCode
from app.models.user import User, UserRole
from app.schemas.qrcode import QRCodeCreate, QRCodeOut

router = APIRouter(tags=["qrcodes"])


def _wa_link(token: str) -> str:
    number_digits = settings.twilio_whatsapp_number.replace("whatsapp:", "").replace("+", "")
    text = urllib.parse.quote(f"QR:{token}")
    return f"https://wa.me/{number_digits}?text={text}"


def _to_out(qr: QRCode) -> QRCodeOut:
    out = QRCodeOut.model_validate(qr)
    out.wa_link = _wa_link(qr.token)
    return out


@router.post("/venues/{venue_id}/qr-codes", response_model=QRCodeOut, status_code=201)
async def create_qr_code(
    venue_id: str,
    payload: QRCodeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.BUSINESS_OWNER, UserRole.SAAS_OWNER)),
) -> QRCodeOut:
    await require_venue_access(venue_id, current_user, db)

    token = secrets.token_urlsafe(16)
    qr = QRCode(venue_id=venue_id, token=token, label=payload.label)
    db.add(qr)
    await db.commit()
    await db.refresh(qr)
    return _to_out(qr)


@router.get("/venues/{venue_id}/qr-codes", response_model=list[QRCodeOut])
async def list_qr_codes(
    venue_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[QRCodeOut]:
    await require_venue_access(venue_id, current_user, db)
    result = await db.execute(select(QRCode).where(QRCode.venue_id == venue_id))
    return [_to_out(qr) for qr in result.scalars().all()]


@router.get("/qr-codes/{qr_code_id}/image")
async def get_qr_code_image(qr_code_id: str, db: AsyncSession = Depends(get_db)) -> Response:
    # Deliberately public/unauthenticated -- it's just a PNG meant to be
    # printed and scanned by guests who have no account.
    qr = await db.get(QRCode, qr_code_id)
    if qr is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "QR code not found")

    img = qrcode.make(_wa_link(qr.token))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Response(content=buf.getvalue(), media_type="image/png")
