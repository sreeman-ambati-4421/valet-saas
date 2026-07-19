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


settings = Settings()
