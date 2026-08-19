from functools import lru_cache

from app.services.analyzed_folders import AnalyzedFolderService
from app.services.groq import GroqService
from app.services.memory import ConversationMemory
from app.services.vectorstore import VectorStore


# ==================================================
# LAZY SERVICE ACCESSORS
# ==================================================

# Instantiating these services loads the FastEmbed model and opens the
# PostgreSQL pool (plus CREATE TABLE statements). Building them lazily keeps
# application import/startup fast, so lightweight endpoints such as
# /api/auth/me answer immediately after a cold start.


@lru_cache(maxsize=1)
def get_vector_store() -> VectorStore:
    return VectorStore()


@lru_cache(maxsize=1)
def get_folder_service() -> AnalyzedFolderService:
    return AnalyzedFolderService()


@lru_cache(maxsize=1)
def get_conversation_memory() -> ConversationMemory:
    return ConversationMemory()


@lru_cache(maxsize=1)
def get_groq_service() -> GroqService:
    return GroqService()


# ==================================================
# WARMUP
# ==================================================

def warmup_services() -> None:
    """Build every heavy singleton ahead of the first request."""

    get_vector_store()
    get_folder_service()
    get_conversation_memory()
