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
    # Gemini model name — overridable via LANGTUTOR_GEMINI_MODEL.
    # Default matches REQUIREMENTS.md §2. Alternatives: "gemini-2.5-flash",
    # "gemini-2.5-pro", "gemini-1.5-pro" (higher quality, slower).
    gemini_model: str = "gemini-1.5-flash"

    livekit_url: str = "http://localhost:7880"
    livekit_api_key: str = "devkey"
    livekit_api_secret: str = "secret"

    # Self-hosted AI services (see docker-compose.ai.yml).
    # When the backend runs on the host and the AI stack runs in Docker,
    # localhost works. When both are in the same compose network, override
    # via LANGTUTOR_STT_BASE_URL=http://stt:8000 etc.
    stt_base_url: str = "http://localhost:8010"
    tts_base_url: str = "http://localhost:8011"
    avatar_base_url: str = "http://localhost:8012"

    # Default off — LivePortrait needs ~3.5 GB VRAM and may OOM on 8 GB
    # cards once STT + TTS are loaded. Flip on once you've verified
    # headroom with `nvidia-smi` during a call.
    avatar_enabled: bool = False

    # Model names — change to trade latency for quality.
    stt_model: str = "Systran/faster-whisper-base.en"

    model_config = {
        "env_prefix": "LANGTUTOR_",
        "env_file": ".env",
    }


settings = Settings()
