from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    APP_NAME: str = "Zentra"

    APP_VERSION: str = "1.0.0"

    SESSION_SECRET: str = "change-me"

    # ==================================================
    # GOOGLE
    # ==================================================

    GOOGLE_CLIENT_ID: str = ""

    GOOGLE_CLIENT_SECRET: str = ""

    GOOGLE_REDIRECT_URI: str = (
        "https://gdrive-rag-system.vercel.app/api/auth/google/callback"
    )

    FRONTEND_URL: str = (
        "https://gdrive-rag-system.vercel.app"
    )

    SESSION_COOKIE_SAMESITE: str = "none"

    SESSION_COOKIE_SECURE: bool = True

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
        "openai/gpt-oss-120b"
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