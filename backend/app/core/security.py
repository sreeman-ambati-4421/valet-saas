from jose import JWTError, jwt

from app.core.config import settings


class InvalidTokenError(Exception):
    pass


def decode_supabase_jwt(token: str) -> dict:
    """Verify and decode a Supabase-issued access token.

    Supabase signs project JWTs with HS256 using the project's JWT secret
    (Settings -> API -> JWT Secret in the Supabase dashboard).
    """
    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except JWTError as exc:
        raise InvalidTokenError(str(exc)) from exc
    return payload
