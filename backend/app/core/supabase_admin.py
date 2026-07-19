import httpx

from app.core.config import settings


class StaffInviteError(Exception):
    pass


def create_invite_link(email: str, redirect_to: str) -> tuple[str, str]:
    """Creates an invited Supabase auth user and returns (user_id, action_link),
    without Supabase sending anything itself.

    Supabase's own email delivery is rate-limited and unreliable on the free
    tier; we take the raw link this endpoint hands back and deliver it
    ourselves via WhatsApp instead. Same underlying account/link mechanism
    as a normal email invite -- only the delivery channel changes.
    """
    url = f"{settings.supabase_url}/auth/v1/admin/generate_link"
    headers = {
        "apikey": settings.supabase_service_key,
        "Authorization": f"Bearer {settings.supabase_service_key}",
        "Content-Type": "application/json",
    }
    # Unlike /auth/v1/invite, generate_link takes redirect_to as a top-level
    # field, not nested under "options" -- nesting it silently gets ignored
    # and Supabase falls back to the project's default Site URL instead.
    body = {"type": "invite", "email": email, "redirect_to": redirect_to}

    try:
        resp = httpx.post(url, headers=headers, json=body, timeout=10)
    except httpx.HTTPError as exc:
        raise StaffInviteError(f"Could not reach Supabase to create invite link: {exc}") from exc

    if resp.status_code >= 400:
        try:
            detail = resp.json().get("msg") or resp.json().get("error_description") or resp.text
        except Exception:
            detail = resp.text
        raise StaffInviteError(detail)

    data = resp.json()
    action_link = data.get("action_link") or data.get("properties", {}).get("action_link")
    user_id = data.get("id") or data.get("user", {}).get("id")
    if not action_link or not user_id:
        raise StaffInviteError("Supabase generate_link response missing action_link or user id")
    return user_id, action_link
