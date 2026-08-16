import os

from dotenv import load_dotenv
from pydantic_settings import BaseSettings


load_dotenv()


class Settings(BaseSettings):

    APP_NAME: str = os.getenv(
        "APP_NAME",
        "Google Drive RAG API"
    )

    APP_VERSION: str = os.getenv(
        "APP_VERSION",
        "1.0.0"
    )

    CHROMA_DB_PATH: str = os.getenv(
        "CHROMA_DB_PATH",
        "./data/chroma_db"
    )

    OLLAMA_BASE_URL: str = os.getenv(
        "OLLAMA_BASE_URL",
        "http://localhost:11434"
    )

    OLLAMA_MODEL: str = os.getenv(
        "OLLAMA_MODEL",
        "qwen3:8b"
    )

    EMBEDDING_MODEL: str = os.getenv(
        "EMBEDDING_MODEL",
        "BAAI/bge-small-en-v1.5"
    )

    CHUNK_SIZE: int = int(
        os.getenv(
            "CHUNK_SIZE",
            "1000"
        )
    )

    CHUNK_OVERLAP: int = int(
        os.getenv(
            "CHUNK_OVERLAP",
            "150"
        )
    )

    TOP_K: int = int(
        os.getenv(
            "TOP_K",
            "5"
        )
    )

    # ==============================================
    # Google OAuth
    # ==============================================

    GOOGLE_CLIENT_ID: str = os.getenv(
        "GOOGLE_CLIENT_ID",
        ""
    )

    GOOGLE_CLIENT_SECRET: str = os.getenv(
        "GOOGLE_CLIENT_SECRET",
        ""
    )

    GOOGLE_REDIRECT_URI: str = os.getenv(
        "GOOGLE_REDIRECT_URI",
        "http://localhost:8000/api/auth/google/callback"
    )

    SESSION_SECRET: str = os.getenv(
        "SESSION_SECRET",
        ""
    )
    # ==============================================
    # LLM Provider
    # ==============================================

    LLM_PROVIDER: str = os.getenv(
        "LLM_PROVIDER",
        "lmstudio"
    )

    LM_STUDIO_BASE_URL: str = os.getenv(
        "LM_STUDIO_BASE_URL",
        "http://localhost:1234"
    )

    LM_STUDIO_MODEL: str = os.getenv(
        "LM_STUDIO_MODEL",
        "llama-3.2-3b-instruct"
    )

settings = Settings()