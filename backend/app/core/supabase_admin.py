import httpx

from app.core.config import settings


class StaffInviteError(Exception):
    pass


def invite_user(email: str, redirect_to: str) -> str:
    """Invite a new user via Supabase's Auth Admin API.

    Sends them an email with a link to set their own password -- no
    password ever passes through our backend or frontend. Returns the
    newly created Supabase auth user's id.
    """
    url = f"{settings.supabase_url}/auth/v1/invite"
    headers = {
        "apikey": settings.supabase_service_key,
        "Authorization": f"Bearer {settings.supabase_service_key}",
        "Content-Type": "application/json",
    }
    body = {"email": email, "options": {"redirect_to": redirect_to}}

    try:
        resp = httpx.post(url, headers=headers, json=body, timeout=10)
    except httpx.HTTPError as exc:
        raise StaffInviteError(f"Could not reach Supabase to send invite: {exc}") from exc

    if resp.status_code >= 400:
        try:
            detail = resp.json().get("msg") or resp.json().get("error_description") or resp.text
        except Exception:
            detail = resp.text
        raise StaffInviteError(detail)

    data = resp.json()
    user_id = data.get("id") or data.get("user", {}).get("id")
    if not user_id:
        raise StaffInviteError("Supabase invite response did not include a user id")
    return user_id
