import threading
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from config import settings

_pool = None
_pool_lock = threading.Lock()


def get_db_pool() -> ConnectionPool:
    """
    Returns a shared ConnectionPool singleton across all services.

    By using a shared pool with a small max_size (e.g. 4), we prevent
    opening multiple independent connection pools across VectorStore,
    AnalyzedFolderService, and ConversationMemory, which would otherwise
    exceed Supabase's connection limit (EMAXCONNSESSION pool_size: 15).
    """
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                if not settings.DATABASE_URL:
                    raise ValueError("DATABASE_URL is not configured.")
                _pool = ConnectionPool(
                    conninfo=settings.DATABASE_URL,
                    min_size=1,
                    max_size=4,
                    timeout=30,
                    kwargs={
                        "row_factory": dict_row,
                    },
                    open=True,
                )
    return _pool
