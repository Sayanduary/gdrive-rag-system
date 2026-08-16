from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    APP_NAME: str = "Google Drive RAG"

    APP_VERSION: str = "1.0.0"

    SESSION_SECRET: str = "change-me"

    GOOGLE_CLIENT_ID: str = ""

    GOOGLE_CLIENT_SECRET: str = ""

    GOOGLE_REDIRECT_URI: str = (
        "http://localhost:8000/api/auth/google/callback"
    )

    TOP_K: int = 8

    # ==================================================
    # LM STUDIO
    # ==================================================

    LM_STUDIO_BASE_URL: str = (
        "http://localhost:1234"
    )

    LM_STUDIO_MODEL: str = (
        "llama-3.2-3b-instruct"
    )

    LM_STUDIO_VISION_MODEL: str = (
        "qwen2.5-vl-3b-instruct"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()