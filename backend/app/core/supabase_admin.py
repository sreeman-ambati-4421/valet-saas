import httpx

from app.core.config import settings


class StaffInviteError(Exception):
    pass


def create_phone_confirmed_user(phone_number: str, full_name: str) -> str:
    """Creates a Supabase Auth user identified by phone number, pre-confirmed
    so they can sign in immediately via WhatsApp OTP -- no invite link or
    token involved, so there's nothing for WhatsApp's link-preview fetcher
    to prematurely consume and nothing for the recipient to click. Returns
    the new Supabase Auth user id.
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
