from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Defaults to a local SQLite file so the app and test suite run out of the box
    # without Supabase credentials. Override with a real Supabase Postgres URL
    # (postgresql+asyncpg://...) via .env for real development/production use.
    database_url: str = "sqlite+aiosqlite:///./dev.db"

    supabase_url: str = ""
    supabase_jwt_secret: str = "dev-only-insecure-secret-change-me"
    supabase_service_key: str = ""

    # Signs our own short-lived accept-invite tokens (sent as a link over
    # WhatsApp). Deliberately separate from supabase_jwt_secret -- these
    # tokens serve a different purpose (one-time password-set, verified by
    # our own backend) and must never be accepted anywhere a real Supabase
    # session token is expected, or vice versa.
    invite_token_secret: str = "dev-only-insecure-invite-secret-change-me"

    cors_origins: list[str] = ["http://localhost:5173"]

    # Used to build the sign-in link mentioned in staff invite WhatsApp messages.
    frontend_url: str = "http://localhost:5173"

    # Meta WhatsApp Cloud API -- direct integration, no BSP middleman.
    # whatsapp_verify_token: arbitrary string you choose; configured both
    # here and in the Meta App dashboard's webhook setup, used only to
    # confirm the GET verification handshake.
    whatsapp_verify_token: str = ""
    # whatsapp_access_token: a System User access token from Meta Business
    # Manager (long-lived, for production -- not the 24h test token).
    whatsapp_access_token: str = ""
    # whatsapp_phone_number_id: the Phone Number ID (not the phone number
    # itself) shown in Meta's WhatsApp Business Platform settings --
    # that's what the Cloud API's /messages endpoint is addressed to.
    whatsapp_phone_number_id: str = ""
    # whatsapp_app_secret: the Meta App's secret, used to verify the
    # X-Hub-Signature-256 header on inbound webhook calls.
    whatsapp_app_secret: str = ""
    # whatsapp_display_phone_number: the actual dialable WhatsApp number
    # (digits only, e.g. "919876543210") guests scan into a wa.me link --
    # distinct from whatsapp_phone_number_id, which the Cloud API itself uses.
    whatsapp_display_phone_number: str = ""


settings = Settings()
