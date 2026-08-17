from datetime import datetime, timezone
from typing import Any

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from config import settings


class ConversationMemory:
    """
    Persistent PostgreSQL conversation storage.

    Uses the same Supabase PostgreSQL database as the
    document_chunks / pgvector storage.
    """

    def __init__(self):
        if not settings.DATABASE_URL:
            raise RuntimeError(
                "DATABASE_URL is not configured."
            )

        self.pool = ConnectionPool(
            conninfo=settings.DATABASE_URL,
            min_size=1,
            max_size=5,
            timeout=30,
            kwargs={
                "row_factory": dict_row,
            },
        )

        self.create_tables()

    # ==================================================
    # DATABASE INITIALIZATION
    # ==================================================

    def create_tables(self):
        with self.pool.connection() as connection:
            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS public.conversations (
                        id BIGSERIAL PRIMARY KEY,

                        user_id TEXT NOT NULL,

                        folder_id TEXT,

                        title TEXT NOT NULL DEFAULT 'New Chat',

                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )

                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS public.messages (
                        id BIGSERIAL PRIMARY KEY,

                        conversation_id BIGINT NOT NULL,

                        role TEXT NOT NULL,

                        content TEXT NOT NULL,

                        sources JSONB NOT NULL DEFAULT '[]'::jsonb,

                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

                        CONSTRAINT fk_messages_conversation
                            FOREIGN KEY (conversation_id)
                            REFERENCES public.conversations(id)
                            ON DELETE CASCADE
                    )
                    """
                )

                # ------------------------------------------
                # Indexes
                # ------------------------------------------

                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS
                    idx_conversations_user_id
                    ON public.conversations(user_id)
                    """
                )

                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS
                    idx_conversations_user_updated
                    ON public.conversations(
                        user_id,
                        updated_at DESC
                    )
                    """
                )

                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS
                    idx_conversations_folder_id
                    ON public.conversations(folder_id)
                    """
                )

                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS
                    idx_messages_conversation_id
                    ON public.messages(conversation_id)
                    """
                )

            connection.commit()

    # ==================================================
    # CREATE CONVERSATION
    # ==================================================

    def create_conversation(
        self,
        user_id: str,
        folder_id: str | None = None,
        title: str = "New Chat",
    ) -> int:

        if not user_id:
            raise ValueError(
                "user_id is required."
            )

        now = datetime.now(
            timezone.utc
        )

        with self.pool.connection() as connection:
            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    INSERT INTO public.conversations (
                        user_id,
                        folder_id,
                        title,
                        created_at,
                        updated_at
                    )
                    VALUES (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                    RETURNING id
                    """,
                    (
                        user_id,
                        folder_id,
                        title,
                        now,
                        now,
                    ),
                )

                row = cursor.fetchone()

            connection.commit()

        return int(row["id"])

    # ==================================================
    # ADD MESSAGE
    # ==================================================

    def add_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        sources: list | None = None,
    ):
        if not conversation_id:
            raise ValueError(
                "conversation_id is required."
            )

        if not role:
            raise ValueError(
                "role is required."
            )

        if content is None:
            content = ""

        now = datetime.now(
            timezone.utc
        )

        with self.pool.connection() as connection:
            with connection.cursor() as cursor:

                # --------------------------------------
                # Insert message only if the conversation
                # exists.
                # --------------------------------------

                cursor.execute(
                    """
                    SELECT id
                    FROM public.conversations
                    WHERE id = %s
                    """,
                    (conversation_id,),
                )

                conversation = cursor.fetchone()

                if not conversation:
                    raise ValueError(
                        "Conversation not found."
                    )

                cursor.execute(
                    """
                    INSERT INTO public.messages (
                        conversation_id,
                        role,
                        content,
                        sources,
                        created_at
                    )
                    VALUES (
                        %s,
                        %s,
                        %s,
                        %s::jsonb,
                        %s
                    )
                    """,
                    (
                        conversation_id,
                        role,
                        content,
                        _json_dumps(
                            sources or []
                        ),
                        now,
                    ),
                )

                # --------------------------------------
                # Update conversation timestamp
                # --------------------------------------

                cursor.execute(
                    """
                    UPDATE public.conversations
                    SET updated_at = %s
                    WHERE id = %s
                    """,
                    (
                        now,
                        conversation_id,
                    ),
                )

            connection.commit()

    # ==================================================
    # GET MESSAGES
    # ==================================================

    def get_messages(
        self,
        conversation_id: int,
        limit: int = 30,
    ):
        with self.pool.connection() as connection:
            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    SELECT
                        role,
                        content,
                        sources,
                        created_at
                    FROM public.messages
                    WHERE conversation_id = %s
                    ORDER BY id DESC
                    LIMIT %s
                    """,
                    (
                        conversation_id,
                        limit,
                    ),
                )

                rows = cursor.fetchall()

        messages = []

        for row in reversed(rows):

            sources = row["sources"]

            if sources is None:
                sources = []

            messages.append(
                {
                    "role": row["role"],
                    "content": row["content"],
                    "sources": sources,
                    "created_at": (
                        row["created_at"].isoformat()
                        if row["created_at"]
                        else None
                    ),
                }
            )

        return messages

    # ==================================================
    # GET USER CONVERSATIONS
    # ==================================================

    def get_user_conversations(
        self,
        user_id: str,
    ):
        if not user_id:
            raise ValueError(
                "user_id is required."
            )

        with self.pool.connection() as connection:
            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    SELECT
                        id,
                        folder_id,
                        title,
                        created_at,
                        updated_at
                    FROM public.conversations
                    WHERE user_id = %s
                    ORDER BY updated_at DESC
                    """,
                    (user_id,),
                )

                rows = cursor.fetchall()

        return [
            {
                "id": row["id"],
                "folder_id": row["folder_id"],
                "title": row["title"],
                "created_at": (
                    row["created_at"].isoformat()
                    if row["created_at"]
                    else None
                ),
                "updated_at": (
                    row["updated_at"].isoformat()
                    if row["updated_at"]
                    else None
                ),
            }
            for row in rows
        ]

    # ==================================================
    # GET CONVERSATION FOLDER
    # ==================================================

    def get_conversation_folder(
        self,
        conversation_id: int,
        user_id: str,
    ):
        with self.pool.connection() as connection:
            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    SELECT folder_id
                    FROM public.conversations
                    WHERE id = %s
                      AND user_id = %s
                    """,
                    (
                        conversation_id,
                        user_id,
                    ),
                )

                row = cursor.fetchone()

        if not row:
            return None

        return row["folder_id"]

    # ==================================================
    # GET CONVERSATION
    # ==================================================

    def get_conversation(
        self,
        conversation_id: int,
        user_id: str,
    ):
        with self.pool.connection() as connection:
            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    SELECT
                        id,
                        user_id,
                        folder_id,
                        title,
                        created_at,
                        updated_at
                    FROM public.conversations
                    WHERE id = %s
                      AND user_id = %s
                    """,
                    (
                        conversation_id,
                        user_id,
                    ),
                )

                row = cursor.fetchone()

        if not row:
            return None

        return {
            "id": row["id"],
            "user_id": row["user_id"],
            "folder_id": row["folder_id"],
            "title": row["title"],
            "created_at": (
                row["created_at"].isoformat()
                if row["created_at"]
                else None
            ),
            "updated_at": (
                row["updated_at"].isoformat()
                if row["updated_at"]
                else None
            ),
        }

    # ==================================================
    # OWNERSHIP CHECK
    # ==================================================

    def conversation_belongs_to_user(
        self,
        conversation_id: int,
        user_id: str,
    ) -> bool:

        with self.pool.connection() as connection:
            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    SELECT 1
                    FROM public.conversations
                    WHERE id = %s
                      AND user_id = %s
                    LIMIT 1
                    """,
                    (
                        conversation_id,
                        user_id,
                    ),
                )

                row = cursor.fetchone()

        return row is not None

    # ==================================================
    # RENAME CONVERSATION
    # ==================================================

    def rename_conversation(
        self,
        conversation_id: int,
        user_id: str,
        title: str,
    ):
        if not title:
            raise ValueError(
                "title is required."
            )

        now = datetime.now(
            timezone.utc
        )

        with self.pool.connection() as connection:
            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    UPDATE public.conversations
                    SET
                        title = %s,
                        updated_at = %s
                    WHERE id = %s
                      AND user_id = %s
                    """,
                    (
                        title,
                        now,
                        conversation_id,
                        user_id,
                    ),
                )

            connection.commit()

    # ==================================================
    # DELETE CONVERSATION
    # ==================================================

    def delete_conversation(
        self,
        conversation_id: int,
        user_id: str,
    ):
        with self.pool.connection() as connection:
            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    DELETE FROM public.conversations
                    WHERE id = %s
                      AND user_id = %s
                    """,
                    (
                        conversation_id,
                        user_id,
                    ),
                )

                deleted = cursor.rowcount

            connection.commit()

        return deleted > 0

    # ==================================================
    # UPDATE CONVERSATION FOLDER
    # ==================================================

    def update_conversation_folder(
        self,
        conversation_id: int,
        user_id: str,
        folder_id: str,
    ):
        now = datetime.now(
            timezone.utc
        )

        with self.pool.connection() as connection:
            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    UPDATE public.conversations
                    SET
                        folder_id = %s,
                        updated_at = %s
                    WHERE id = %s
                      AND user_id = %s
                    """,
                    (
                        folder_id,
                        now,
                        conversation_id,
                        user_id,
                    ),
                )

            connection.commit()

    # ==================================================
    # CLOSE
    # ==================================================

    def close(self):
        self.pool.close()


# ======================================================
# JSON HELPER
# ======================================================

def _json_dumps(value: Any) -> str:
    import json

    return json.dumps(
        value,
        ensure_ascii=False,
    )