from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    APP_NAME: str = "Google Drive RAG"

    APP_VERSION: str = "1.0.0"

    SESSION_SECRET: str = "change-me"

    # ==================================================
    # GOOGLE
    # ==================================================

    GOOGLE_CLIENT_ID: str = ""

    GOOGLE_CLIENT_SECRET: str = ""

    GOOGLE_REDIRECT_URI: str = (
        "http://localhost:8000/api/auth/google/callback"
    )

    FRONTEND_URL: str = "http://localhost:5173"

    SESSION_COOKIE_SAMESITE: str = "lax"

    SESSION_COOKIE_SECURE: bool = False

    # ==================================================
    # RETRIEVAL
    # ==================================================

    TOP_K: int = 5

    RETRIEVAL_CANDIDATES: int = 100

    # ==================================================
    # EMBEDDINGS
    # ==================================================

    EMBEDDING_MODEL: str = (
        "BAAI/bge-small-en-v1.5"
    )

    # ==================================================
    # CHUNKING
    # ==================================================

    CHUNK_SIZE: int = 1000

    CHUNK_OVERLAP: int = 150

    # ==================================================
    # POSTGRESQL / SUPABASE
    # ==================================================

    DATABASE_URL: str = ""

    # ==================================================
    # GROQ
    # ==================================================

    GROQ_API_KEY: str = ""

    # Normal RAG / chat generation
    GROQ_LLM_MODEL: str = (
        "llama-3.1-8b-instant"
    )

    # Scanned PDF / image OCR
    GROQ_VISION_MODEL: str = (
        "qwen/qwen3.6-27b"
    )

    # ==================================================
    # PROVIDER
    # ==================================================

    LLM_PROVIDER: str = "groq"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()