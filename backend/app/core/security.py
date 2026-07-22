import time

import httpx
from jose import JWTError, jwt

from app.core.config import settings


class InvalidTokenError(Exception):
    pass


INVITE_TOKEN_PURPOSE = "staff_invite_accept"
INVITE_TOKEN_TTL_SECONDS = 7 * 24 * 3600


def create_invite_token(user_id: str) -> str:
    """Signs a short-lived token (our own secret, not Supabase's) identifying
    a pending invited user. Embedded in the accept-invite link sent over
    WhatsApp -- verified by verify_invite_token when they submit a password.
    """
    payload = {
        "sub": user_id,
        "purpose": INVITE_TOKEN_PURPOSE,
        "exp": int(time.time()) + INVITE_TOKEN_TTL_SECONDS,
    }
    return jwt.encode(payload, settings.invite_token_secret, algorithm="HS256")


def verify_invite_token(token: str) -> str:
    """Returns the app-level user id encoded in a valid, unexpired invite token."""
    try:
        payload = jwt.decode(token, settings.invite_token_secret, algorithms=["HS256"])
    except JWTError as exc:
        raise InvalidTokenError(str(exc)) from exc

    if payload.get("purpose") != INVITE_TOKEN_PURPOSE:
        raise InvalidTokenError("Not an invite-accept token")

    user_id = payload.get("sub")
    if not user_id:
        raise InvalidTokenError("Token missing subject claim")
    return user_id


_jwks_cache: dict | None = None


def _fetch_jwks() -> dict:
    global _jwks_cache
    url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
    resp = httpx.get(url, timeout=5)
    resp.raise_for_status()
    _jwks_cache = resp.json()
    return _jwks_cache


def _get_jwk_for_kid(kid: str) -> dict | None:
    jwks = _jwks_cache or _fetch_jwks()
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    # kid not in cache -- key may have rotated (e.g. a standby key was
    # promoted), refresh once before giving up.
    jwks = _fetch_jwks()
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    return None


def decode_supabase_jwt(token: str) -> dict:
    """Verify and decode a Supabase-issued access token.

    Newer Supabase projects sign tokens with an asymmetric key (e.g. ECC
    P-256 / ES256) rather than a single shared HS256 secret, and publish
    the public keys via the project's JWKS endpoint. Older tokens (issued
    before a key rotation) may still be signed with the legacy shared
    secret. We support both: HS256 tokens are verified against
    SUPABASE_JWT_SECRET directly; anything else is verified against the
    matching public key from the JWKS endpoint, looked up by the token's
    `kid` header.
    """
    try:
        header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise InvalidTokenError(str(exc)) from exc

    alg = header.get("alg", "HS256")

    try:
        if alg == "HS256":
            payload = jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
            )
        else:
            kid = header.get("kid")
            signing_key = _get_jwk_for_kid(kid) if kid else None
            if signing_key is None:
                raise InvalidTokenError("No matching signing key found for token")
            payload = jwt.decode(token, signing_key, algorithms=[alg], audience="authenticated")
    except JWTError as exc:
        raise InvalidTokenError(str(exc)) from exc

    return payload
