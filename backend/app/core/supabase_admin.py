import httpx

from app.core.config import settings


class StaffInviteError(Exception):
    pass


def create_phone_confirmed_user(phone_number: str, full_name: str) -> str:
    """Creates a Supabase Auth user identified by phone number, phone-confirmed
    but with no password yet -- Supabase allows an account to exist
    password-less until one is set via set_user_password below, once the
    recipient accepts their invite. Returns the new Supabase Auth user id.
    """
    url = f"{settings.supabase_url}/auth/v1/admin/users"
    headers = {
        "apikey": settings.supabase_service_key,
        "Authorization": f"Bearer {settings.supabase_service_key}",
        "Content-Type": "application/json",
    }
    body = {"phone": phone_number, "phone_confirm": True, "user_metadata": {"full_name": full_name}}

    try:
        resp = httpx.post(url, headers=headers, json=body, timeout=10)
    except httpx.HTTPError as exc:
        raise StaffInviteError(f"Could not reach Supabase to create the account: {exc}") from exc

    if resp.status_code >= 400:
        try:
            detail = resp.json().get("msg") or resp.json().get("error_description") or resp.text
        except Exception:
            detail = resp.text
        raise StaffInviteError(detail)

    user_id = resp.json().get("id")
    if not user_id:
        raise StaffInviteError("Supabase admin/users response missing user id")
    return user_id


def set_user_password(supabase_user_id: str, password: str) -> None:
    """Sets (or replaces) the password on an existing Supabase Auth user --
    used when a staff member accepts their invite and chooses a password."""
    url = f"{settings.supabase_url}/auth/v1/admin/users/{supabase_user_id}"
    headers = {
        "apikey": settings.supabase_service_key,
        "Authorization": f"Bearer {settings.supabase_service_key}",
        "Content-Type": "application/json",
    }

    try:
        resp = httpx.put(url, headers=headers, json={"password": password}, timeout=10)
    except httpx.HTTPError as exc:
        raise StaffInviteError(f"Could not reach Supabase to set the password: {exc}") from exc

    if resp.status_code >= 400:
        try:
            detail = resp.json().get("msg") or resp.json().get("error_description") or resp.text
        except Exception:
            detail = resp.text
        raise StaffInviteError(detail)
