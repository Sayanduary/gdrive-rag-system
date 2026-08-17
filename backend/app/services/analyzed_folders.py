from datetime import datetime, timezone

from app.db import get_db_pool
from config import settings


class AnalyzedFolderService:
    """
    Persistent registry for analyzed Google Drive folders/files.

    This service does NOT replace document_chunks.

    document_chunks:
        RAG source of truth

    analyzed_folders:
        UI / folder registry

    analyzed_files:
        UI / file registry
    """

    # ==================================================
    # INITIALIZATION
    # ==================================================

    def __init__(self):

        self.pool = get_db_pool()
        self.create_tables()

    # ==================================================
    # CREATE TABLES
    # ==================================================

    def create_tables(self):

        with self.pool.connection() as connection:

            with connection.cursor() as cursor:

                # ------------------------------------------
                # ANALYZED FOLDERS
                # ------------------------------------------

                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS
                    public.analyzed_folders (

                        id BIGSERIAL PRIMARY KEY,

                        user_id TEXT NOT NULL,

                        folder_id TEXT NOT NULL,

                        folder_name TEXT NOT NULL
                            DEFAULT 'Google Drive Folder',

                        folder_url TEXT,

                        file_count INTEGER NOT NULL
                            DEFAULT 0,

                        chunk_count INTEGER NOT NULL
                            DEFAULT 0,

                        analyzed_at TIMESTAMPTZ
                            NOT NULL DEFAULT NOW(),

                        updated_at TIMESTAMPTZ
                            NOT NULL DEFAULT NOW(),

                        UNIQUE (
                            user_id,
                            folder_id
                        )
                    )
                    """
                )

                # ------------------------------------------
                # ANALYZED FILES
                # ------------------------------------------

                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS
                    public.analyzed_files (

                        id BIGSERIAL PRIMARY KEY,

                        user_id TEXT NOT NULL,

                        folder_id TEXT NOT NULL,

                        file_id TEXT NOT NULL,

                        file_name TEXT NOT NULL,

                        path TEXT,

                        mime_type TEXT,

                        modified_time TIMESTAMPTZ,

                        chunk_count INTEGER NOT NULL
                            DEFAULT 0,

                        analyzed_at TIMESTAMPTZ
                            NOT NULL DEFAULT NOW(),

                        updated_at TIMESTAMPTZ
                            NOT NULL DEFAULT NOW(),

                        UNIQUE (
                            user_id,
                            folder_id,
                            file_id
                        )
                    )
                    """
                )

                # ------------------------------------------
                # FOLDER INDEXES
                # ------------------------------------------

                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS
                    idx_analyzed_folders_user

                    ON public.analyzed_folders(
                        user_id
                    )
                    """
                )

                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS
                    idx_analyzed_folders_user_updated

                    ON public.analyzed_folders(
                        user_id,
                        updated_at DESC
                    )
                    """
                )

                # ------------------------------------------
                # FILE INDEXES
                # ------------------------------------------

                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS
                    idx_analyzed_files_user

                    ON public.analyzed_files(
                        user_id
                    )
                    """
                )

                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS
                    idx_analyzed_files_user_folder

                    ON public.analyzed_files(
                        user_id,
                        folder_id
                    )
                    """
                )

            connection.commit()

    # ==================================================
    # UPSERT FOLDER
    # ==================================================

    def upsert_folder(
        self,
        user_id: str,
        folder_id: str,
        folder_name: str,
        folder_url: str | None,
        file_count: int,
        chunk_count: int,
    ):

        if not user_id:
            raise ValueError(
                "user_id is required."
            )

        if not folder_id:
            raise ValueError(
                "folder_id is required."
            )

        now = datetime.now(
            timezone.utc
        )

        with self.pool.connection() as connection:

            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    INSERT INTO public.analyzed_folders (
                        user_id,
                        folder_id,
                        folder_name,
                        folder_url,
                        file_count,
                        chunk_count,
                        analyzed_at,
                        updated_at
                    )
                    VALUES (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )

                    ON CONFLICT (
                        user_id,
                        folder_id
                    )

                    DO UPDATE SET

                        folder_name =
                            EXCLUDED.folder_name,

                        folder_url =
                            EXCLUDED.folder_url,

                        file_count =
                            EXCLUDED.file_count,

                        chunk_count =
                            EXCLUDED.chunk_count,

                        updated_at =
                            EXCLUDED.updated_at
                    """,
                    (
                        user_id,
                        folder_id,
                        folder_name,
                        folder_url,
                        int(file_count),
                        int(chunk_count),
                        now,
                        now,
                    ),
                )

            connection.commit()

    # ==================================================
    # UPSERT FILE
    # ==================================================

    def upsert_file(
        self,
        user_id: str,
        folder_id: str,
        file_id: str,
        file_name: str,
        path: str | None = None,
        mime_type: str | None = None,
        modified_time=None,
        chunk_count: int = 0,
    ):

        if not user_id:
            raise ValueError(
                "user_id is required."
            )

        if not folder_id:
            raise ValueError(
                "folder_id is required."
            )

        if not file_id:
            raise ValueError(
                "file_id is required."
            )

        now = datetime.now(
            timezone.utc
        )

        with self.pool.connection() as connection:

            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    INSERT INTO public.analyzed_files (
                        user_id,
                        folder_id,
                        file_id,
                        file_name,
                        path,
                        mime_type,
                        modified_time,
                        chunk_count,
                        analyzed_at,
                        updated_at
                    )
                    VALUES (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )

                    ON CONFLICT (
                        user_id,
                        folder_id,
                        file_id
                    )

                    DO UPDATE SET

                        file_name =
                            EXCLUDED.file_name,

                        path =
                            EXCLUDED.path,

                        mime_type =
                            EXCLUDED.mime_type,

                        modified_time =
                            EXCLUDED.modified_time,

                        chunk_count =
                            EXCLUDED.chunk_count,

                        updated_at =
                            EXCLUDED.updated_at
                    """,
                    (
                        user_id,
                        folder_id,
                        file_id,
                        file_name,
                        path,
                        mime_type,
                        modified_time,
                        int(chunk_count),
                        now,
                        now,
                    ),
                )

            connection.commit()

    # ==================================================
    # UPSERT FILES IN BATCH
    # ==================================================

    def upsert_files(
        self,
        files: list[dict],
    ):

        if not files:
            return

        now = datetime.now(
            timezone.utc
        )

        rows = []

        for item in files:

            rows.append(
                (
                    item["user_id"],
                    item["folder_id"],
                    item["file_id"],
                    item["file_name"],
                    item.get("path"),
                    item.get("mime_type"),
                    item.get("modified_time"),
                    int(
                        item.get(
                            "chunk_count",
                            0,
                        )
                    ),
                    now,
                    now,
                )
            )

        with self.pool.connection() as connection:

            with connection.cursor() as cursor:

                cursor.executemany(
                    """
                    INSERT INTO public.analyzed_files (
                        user_id,
                        folder_id,
                        file_id,
                        file_name,
                        path,
                        mime_type,
                        modified_time,
                        chunk_count,
                        analyzed_at,
                        updated_at
                    )
                    VALUES (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )

                    ON CONFLICT (
                        user_id,
                        folder_id,
                        file_id
                    )

                    DO UPDATE SET

                        file_name =
                            EXCLUDED.file_name,

                        path =
                            EXCLUDED.path,

                        mime_type =
                            EXCLUDED.mime_type,

                        modified_time =
                            EXCLUDED.modified_time,

                        chunk_count =
                            EXCLUDED.chunk_count,

                        updated_at =
                            EXCLUDED.updated_at
                    """,
                    rows,
                )

            connection.commit()

    # ==================================================
    # LIST USER FOLDERS
    # ==================================================

    def get_user_folders(
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
                        folder_id,
                        folder_name,
                        folder_url,
                        file_count,
                        chunk_count,
                        analyzed_at,
                        updated_at

                    FROM public.analyzed_folders

                    WHERE user_id = %s

                    ORDER BY updated_at DESC
                    """,
                    (
                        user_id,
                    ),
                )

                return cursor.fetchall()

    # ==================================================
    # GET LATEST ANALYZED FOLDER
    # ==================================================

    def get_latest_user_folder(
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
                        folder_id

                    FROM public.analyzed_folders

                    WHERE user_id = %s

                    ORDER BY
                        updated_at DESC

                    LIMIT 1
                    """,
                    (
                        user_id,
                    ),
                )

                row = cursor.fetchone()

        if not row:
            return None

        return row["folder_id"]

    # ==================================================
    # GET FOLDER
    # ==================================================

    def get_folder(
        self,
        user_id: str,
        folder_id: str,
    ):

        if not user_id:
            raise ValueError(
                "user_id is required."
            )

        if not folder_id:
            raise ValueError(
                "folder_id is required."
            )

        with self.pool.connection() as connection:

            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    SELECT
                        folder_id,
                        folder_name,
                        folder_url,
                        file_count,
                        chunk_count,
                        analyzed_at,
                        updated_at

                    FROM public.analyzed_folders

                    WHERE user_id = %s
                      AND folder_id = %s
                    """,
                    (
                        user_id,
                        folder_id,
                    ),
                )

                return cursor.fetchone()

    # ==================================================
    # LIST FOLDER FILES
    # ==================================================

    def get_folder_files(
        self,
        user_id: str,
        folder_id: str,
    ):

        if not user_id:
            raise ValueError(
                "user_id is required."
            )

        if not folder_id:
            raise ValueError(
                "folder_id is required."
            )

        with self.pool.connection() as connection:

            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    SELECT
                        file_id,
                        file_name,
                        path,
                        mime_type,
                        modified_time,
                        chunk_count,
                        analyzed_at,
                        updated_at

                    FROM public.analyzed_files

                    WHERE user_id = %s
                      AND folder_id = %s

                    ORDER BY file_name ASC
                    """,
                    (
                        user_id,
                        folder_id,
                    ),
                )

                return cursor.fetchall()

    # ==================================================
    # DELETE FILE
    # ==================================================

    def delete_file(
        self,
        user_id: str,
        folder_id: str,
        file_id: str,
    ):
        """
        Remove a file from Zentra's index.

        This does NOT delete the actual
        Google Drive file.
        """

        if not user_id:
            raise ValueError(
                "user_id is required."
            )

        if not folder_id:
            raise ValueError(
                "folder_id is required."
            )

        if not file_id:
            raise ValueError(
                "file_id is required."
            )

        with self.pool.connection() as connection:

            with connection.cursor() as cursor:

                # ------------------------------------------
                # DELETE VECTOR CHUNKS
                # ------------------------------------------

                cursor.execute(
                    """
                    DELETE FROM public.document_chunks

                    WHERE user_id = %s
                      AND folder_id = %s
                      AND file_id = %s
                    """,
                    (
                        user_id,
                        folder_id,
                        file_id,
                    ),
                )

                deleted_chunks = (
                    cursor.rowcount
                )

                # ------------------------------------------
                # DELETE FILE REGISTRY
                # ------------------------------------------

                cursor.execute(
                    """
                    DELETE FROM public.analyzed_files

                    WHERE user_id = %s
                      AND folder_id = %s
                      AND file_id = %s
                    """,
                    (
                        user_id,
                        folder_id,
                        file_id,
                    ),
                )

                deleted_file = (
                    cursor.rowcount
                )

                # ------------------------------------------
                # RECALCULATE FOLDER COUNTS
                # ------------------------------------------

                cursor.execute(
                    """
                    SELECT

                        COUNT(
                            DISTINCT file_id
                        ) AS file_count,

                        COUNT(*) AS chunk_count

                    FROM public.document_chunks

                    WHERE user_id = %s
                      AND folder_id = %s
                    """,
                    (
                        user_id,
                        folder_id,
                    ),
                )

                counts = (
                    cursor.fetchone()
                )

                # ------------------------------------------
                # UPDATE FOLDER REGISTRY
                # ------------------------------------------

                cursor.execute(
                    """
                    UPDATE public.analyzed_folders

                    SET
                        file_count = %s,
                        chunk_count = %s,
                        updated_at = NOW()

                    WHERE user_id = %s
                      AND folder_id = %s
                    """,
                    (
                        int(
                            counts[
                                "file_count"
                            ]
                        ),
                        int(
                            counts[
                                "chunk_count"
                            ]
                        ),
                        user_id,
                        folder_id,
                    ),
                )

            connection.commit()

        return {
            "deleted_file":
                deleted_file > 0,

            "deleted_chunks":
                deleted_chunks,
        }

    # ==================================================
    # DELETE ENTIRE FOLDER
    # ==================================================

    def delete_folder(
        self,
        user_id: str,
        folder_id: str,
    ):
        """
        Remove an analyzed folder from Zentra.

        Deletes:

            document_chunks
            analyzed_files
            analyzed_folders

        Does NOT delete:

            Google Drive files
            conversations
            messages
        """

        if not user_id:
            raise ValueError(
                "user_id is required."
            )

        if not folder_id:
            raise ValueError(
                "folder_id is required."
            )

        with self.pool.connection() as connection:

            with connection.cursor() as cursor:

                # ------------------------------------------
                # COUNT CHUNKS
                # ------------------------------------------

                cursor.execute(
                    """
                    SELECT
                        COUNT(*) AS total

                    FROM public.document_chunks

                    WHERE user_id = %s
                      AND folder_id = %s
                    """,
                    (
                        user_id,
                        folder_id,
                    ),
                )

                chunk_row = (
                    cursor.fetchone()
                )

                deleted_chunks = int(
                    chunk_row["total"]
                )

                # ------------------------------------------
                # DELETE CHUNKS
                # ------------------------------------------

                cursor.execute(
                    """
                    DELETE FROM public.document_chunks

                    WHERE user_id = %s
                      AND folder_id = %s
                    """,
                    (
                        user_id,
                        folder_id,
                    ),
                )

                # ------------------------------------------
                # DELETE FILE REGISTRY
                # ------------------------------------------

                cursor.execute(
                    """
                    DELETE FROM public.analyzed_files

                    WHERE user_id = %s
                      AND folder_id = %s
                    """,
                    (
                        user_id,
                        folder_id,
                    ),
                )

                deleted_files = (
                    cursor.rowcount
                )

                # ------------------------------------------
                # DELETE FOLDER REGISTRY
                # ------------------------------------------

                cursor.execute(
                    """
                    DELETE FROM public.analyzed_folders

                    WHERE user_id = %s
                      AND folder_id = %s
                    """,
                    (
                        user_id,
                        folder_id,
                    ),
                )

                deleted_folder = (
                    cursor.rowcount
                )

            connection.commit()

        return {
            "deleted_folder":
                deleted_folder > 0,

            "deleted_files":
                deleted_files,

            "deleted_chunks":
                deleted_chunks,
        }

    # ==================================================
    # CLOSE
    # ==================================================

    def close(self):

        self.pool.close()