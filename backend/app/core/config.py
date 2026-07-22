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

    cors_origins: list[str] = ["http://localhost:5173"]

    # Used to build the sign-in link mentioned in staff invite WhatsApp messages.
    frontend_url: str = "http://localhost:5173"

    # Twilio WhatsApp integration. Sandbox number by default -- no business
    # verification needed for dev/testing. Swap to a real Sender once one
    # exists.
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_number: str = "whatsapp:+14155238886"

    # The backend's own public URL, used to reconstruct the exact URL Twilio
    # signed when verifying webhook signatures (can't trust request.url
    # directly behind Render's reverse proxy).
    public_base_url: str = "http://localhost:8000"


settings = Settings()
