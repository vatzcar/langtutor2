from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/langtutor"
    test_database_url: str = "sqlite+aiosqlite:///./test.db"
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    google_client_id: str = ""
    apple_client_id: str = ""

    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 10

    gemini_api_key: str = ""

    livekit_url: str = "http://localhost:7880"
    livekit_api_key: str = "devkey"
    livekit_api_secret: str = "secret"

    model_config = {
        "env_prefix": "LANGTUTOR_",
        "env_file": ".env",
    }


settings = Settings()
