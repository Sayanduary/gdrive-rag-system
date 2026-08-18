import threading
from fastembed import TextEmbedding

from app.db import get_db_pool
from config import settings


class VectorStore:

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(VectorStore, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    # ==================================================
    # INITIALIZATION
    # ==================================================

    def __init__(self):
        if getattr(self, "_initialized", False):
            return

        self.embedding_model = TextEmbedding(
            model_name=settings.EMBEDDING_MODEL
        )

        self.pool = get_db_pool()
        self._initialized = True

    # ==================================================
    # CLOSE
    # ==================================================

    def close(self):

        if self.pool:
            self.pool.close()

    # ==================================================
    # EMPTY RESULT
    # ==================================================

    @staticmethod
    def _empty_results() -> dict:

        return {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }

    # ==================================================
    # EMBEDDINGS
    # ==================================================

    def _embed_texts(
        self,
        texts: list[str],
    ) -> list[list[float]]:

        if not texts:
            return []

        embeddings = list(
            self.embedding_model.embed(
                texts
            )
        )

        return [
            embedding.tolist()
            for embedding in embeddings
        ]

    # ==================================================
    # VECTOR LITERAL
    # ==================================================

    @staticmethod
    def _vector_literal(
        embedding: list[float],
    ) -> str:

        return (
            "["
            + ",".join(
                str(float(value))
                for value in embedding
            )
            + "]"
        )

    # ==================================================
    # ADD / UPDATE DOCUMENTS
    # ==================================================

    def add_documents(
        self,
        texts: list[str],
        metadatas: list[dict],
        ids: list[str],
    ):

        if not texts:
            return

        if not (
            len(texts)
            == len(metadatas)
            == len(ids)
        ):
            raise ValueError(
                "texts, metadatas and ids "
                "must have the same length."
            )

        embeddings = self._embed_texts(
            texts
        )

        rows = []

        for index, text in enumerate(
            texts
        ):

            metadata = (
                metadatas[index]
                or {}
            )

            # ------------------------------------------
            # TENANT VALIDATION
            # ------------------------------------------

            user_id = metadata.get(
                "user_id"
            )

            folder_id = metadata.get(
                "folder_id"
            )

            file_id = metadata.get(
                "file_id"
            )

            if not user_id:
                raise ValueError(
                    "Every chunk must contain "
                    "user_id."
                )

            if not folder_id:
                raise ValueError(
                    "Every chunk must contain "
                    "folder_id."
                )

            if not file_id:
                raise ValueError(
                    "Every chunk must contain "
                    "file_id."
                )

            chunk_id = metadata.get(
                "chunk_id",
                index,
            )

            rows.append(
                (
                    ids[index],
                    user_id,
                    folder_id,
                    file_id,
                    metadata.get(
                        "file_name"
                    ),
                    metadata.get(
                        "path"
                    ),
                    metadata.get(
                        "mime_type"
                    ),
                    int(chunk_id),
                    text,
                    metadata.get(
                        "modified_time"
                    ),
                    self._vector_literal(
                        embeddings[index]
                    ),
                )
            )

        sql = """
            INSERT INTO public.document_chunks (
                id,
                user_id,
                folder_id,
                file_id,
                file_name,
                path,
                mime_type,
                chunk_id,
                content,
                modified_time,
                embedding
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
                %s,
                %s::extensions.vector
            )

            ON CONFLICT (id)
            DO UPDATE SET

                user_id =
                    EXCLUDED.user_id,

                folder_id =
                    EXCLUDED.folder_id,

                file_id =
                    EXCLUDED.file_id,

                file_name =
                    EXCLUDED.file_name,

                path =
                    EXCLUDED.path,

                mime_type =
                    EXCLUDED.mime_type,

                chunk_id =
                    EXCLUDED.chunk_id,

                content =
                    EXCLUDED.content,

                modified_time =
                    EXCLUDED.modified_time,

                embedding =
                    EXCLUDED.embedding,

                updated_at =
                    now()
        """

        with self.pool.connection() as connection:

            with connection.cursor() as cursor:

                cursor.executemany(
                    sql,
                    rows,
                )

            connection.commit()

    # ==================================================
    # SEARCH
    # ==================================================

    def search(
        self,
        query: str,
        top_k: int = 5,
        user_id: str | None = None,
        folder_id: str | None = None,
        file_id: str | None = None,
    ):

        if not user_id:

            raise ValueError(
                "user_id is required for "
                "PostgreSQL vector search."
            )

        query = query.strip()

        if not query:

            return self._empty_results()

        if top_k <= 0:

            top_k = 5

        # ------------------------------------------
        # QUERY EMBEDDING
        # ------------------------------------------

        query_embedding = list(
            self.embedding_model.embed(
                [query]
            )
        )[0]

        vector = self._vector_literal(
            query_embedding.tolist()
        )

        # ------------------------------------------
        # TENANT FILTERS
        # ------------------------------------------

        conditions = [
            "user_id = %s"
        ]

        filter_params = [
            user_id
        ]

        if folder_id:

            conditions.append(
                "folder_id = %s"
            )

            filter_params.append(
                folder_id
            )

        if file_id:

            conditions.append(
                "file_id = %s"
            )

            filter_params.append(
                file_id
            )

        where_clause = " AND ".join(
            conditions
        )

        sql = f"""
            SELECT
                id,
                content,
                file_id,
                file_name,
                path,
                mime_type,
                chunk_id,
                user_id,
                folder_id,
                modified_time,

                embedding
                    <=> %s::extensions.vector
                    AS distance

            FROM public.document_chunks

            WHERE {where_clause}

            ORDER BY
                embedding
                    <=> %s::extensions.vector

            LIMIT %s
        """

        parameters = [
            vector,
            *filter_params,
            vector,
            top_k,
        ]

        with self.pool.connection() as connection:

            with connection.cursor() as cursor:

                cursor.execute(
                    sql,
                    parameters,
                )

                rows = cursor.fetchall()

        if not rows:

            return self._empty_results()

        ids = []
        documents = []
        metadatas = []
        distances = []

        for row in rows:

            ids.append(
                row["id"]
            )

            documents.append(
                row["content"]
            )

            metadatas.append(
                {
                    "file_name":
                        row["file_name"],

                    "file_id":
                        row["file_id"],

                    "folder_id":
                        row["folder_id"],

                    "path":
                        row["path"],

                    "mime_type":
                        row["mime_type"],

                    "chunk_id":
                        row["chunk_id"],

                    "user_id":
                        row["user_id"],

                    "modified_time":
                        row["modified_time"],
                }
            )

            distances.append(
                float(
                    row["distance"]
                )
            )

        return {
            "ids": [ids],
            "documents": [
                documents
            ],
            "metadatas": [
                metadatas
            ],
            "distances": [
                distances
            ],
        }

    # ==================================================
    # COUNT CHUNKS
    # ==================================================

    def count(
        self,
        user_id: str,
        folder_id: str | None = None,
    ) -> int:

        if not user_id:

            raise ValueError(
                "user_id is required for count."
            )

        conditions = [
            "user_id = %s"
        ]

        parameters = [
            user_id
        ]

        if folder_id:

            conditions.append(
                "folder_id = %s"
            )

            parameters.append(
                folder_id
            )

        where_clause = " AND ".join(
            conditions
        )

        sql = f"""
            SELECT COUNT(*) AS total

            FROM public.document_chunks

            WHERE {where_clause}
        """

        with self.pool.connection() as connection:

            with connection.cursor() as cursor:

                cursor.execute(
                    sql,
                    parameters,
                )

                row = cursor.fetchone()

        return int(
            row["total"]
        )

    # ==================================================
    # COUNT FILE CHUNKS
    # ==================================================

    def count_file(
        self,
        user_id: str,
        folder_id: str,
        file_id: str,
    ) -> int:

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

        sql = """
            SELECT COUNT(*) AS total
            FROM public.document_chunks

            WHERE user_id = %s
              AND folder_id = %s
              AND file_id = %s
        """

        with self.pool.connection() as connection:

            with connection.cursor() as cursor:

                cursor.execute(
                    sql,
                    (
                        user_id,
                        folder_id,
                        file_id,
                    ),
                )

                row = cursor.fetchone()

        return int(
            row["total"]
        )

    # ==================================================
    # FOLDER FILE COUNT
    # ==================================================

    def get_folder_file_count(
        self,
        user_id: str,
        folder_id: str,
    ) -> int:

        if not user_id:
            raise ValueError(
                "user_id is required."
            )

        if not folder_id:
            raise ValueError(
                "folder_id is required."
            )

        sql = """
            SELECT COUNT(
                DISTINCT file_id
            ) AS total

            FROM public.document_chunks

            WHERE user_id = %s
              AND folder_id = %s
        """

        with self.pool.connection() as connection:

            with connection.cursor() as cursor:

                cursor.execute(
                    sql,
                    (
                        user_id,
                        folder_id,
                    ),
                )

                row = cursor.fetchone()

        return int(
            row["total"]
        )

    # ==================================================
    # FOLDER CHUNK COUNT
    # ==================================================

    def get_folder_chunk_count(
        self,
        user_id: str,
        folder_id: str,
    ) -> int:

        return self.count(
            user_id=user_id,
            folder_id=folder_id,
        )

    # ==================================================
    # GET FILE CHUNKS
    # ==================================================

    def get_file_chunks(
        self,
        file_id: str,
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

        if not file_id:

            raise ValueError(
                "file_id is required."
            )

        sql = """
            SELECT
                id,
                content,
                file_id,
                file_name,
                folder_id,
                path,
                mime_type,
                chunk_id,
                user_id,
                modified_time

            FROM public.document_chunks

            WHERE user_id = %s
              AND folder_id = %s
              AND file_id = %s

            ORDER BY chunk_id
        """

        with self.pool.connection() as connection:

            with connection.cursor() as cursor:

                cursor.execute(
                    sql,
                    (
                        user_id,
                        folder_id,
                        file_id,
                    ),
                )

                rows = cursor.fetchall()

        return {
            "ids": [
                row["id"]
                for row in rows
            ],

            "documents": [
                row["content"]
                for row in rows
            ],

            "metadatas": [
                {
                    "file_name":
                        row["file_name"],

                    "file_id":
                        row["file_id"],

                    "folder_id":
                        row["folder_id"],

                    "path":
                        row["path"],

                    "mime_type":
                        row["mime_type"],

                    "chunk_id":
                        row["chunk_id"],

                    "user_id":
                        row["user_id"],

                    "modified_time":
                        row["modified_time"],
                }
                for row in rows
            ],
        }

    # ==================================================
    # CHECK FILE EXISTS
    # ==================================================

    def file_exists(
        self,
        file_id: str,
        user_id: str,
        folder_id: str,
    ) -> bool:

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

        sql = """
            SELECT 1
            FROM public.document_chunks

            WHERE user_id = %s
              AND folder_id = %s
              AND file_id = %s

            LIMIT 1
        """

        with self.pool.connection() as connection:

            with connection.cursor() as cursor:

                cursor.execute(
                    sql,
                    (
                        user_id,
                        folder_id,
                        file_id,
                    ),
                )

                return (
                    cursor.fetchone()
                    is not None
                )

    # ==================================================
    # GET FILE MODIFICATION TIME
    # ==================================================

    def get_file_modified_time(
        self,
        file_id: str,
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

        if not file_id:
            raise ValueError(
                "file_id is required."
            )

        sql = """
            SELECT modified_time

            FROM public.document_chunks

            WHERE user_id = %s
              AND folder_id = %s
              AND file_id = %s

            ORDER BY chunk_id

            LIMIT 1
        """

        with self.pool.connection() as connection:

            with connection.cursor() as cursor:

                cursor.execute(
                    sql,
                    (
                        user_id,
                        folder_id,
                        file_id,
                    ),
                )

                row = cursor.fetchone()

        if not row:
            return None

        return row["modified_time"]

    # ==================================================
    # DELETE FILE
    # ==================================================

    def delete_file(
        self,
        file_id: str,
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

        if not file_id:
            raise ValueError(
                "file_id is required."
            )

        sql = """
            DELETE FROM public.document_chunks

            WHERE user_id = %s
              AND folder_id = %s
              AND file_id = %s
        """

        with self.pool.connection() as connection:

            with connection.cursor() as cursor:

                cursor.execute(
                    sql,
                    (
                        user_id,
                        folder_id,
                        file_id,
                    ),
                )

                deleted_chunks = (
                    cursor.rowcount
                )

            connection.commit()

        return deleted_chunks

    # ==================================================
    # DELETE ENTIRE FOLDER
    # ==================================================

    def delete_folder(
        self,
        user_id: str,
        folder_id: str,
    ) -> int:

        if not user_id:
            raise ValueError(
                "user_id is required."
            )

        if not folder_id:
            raise ValueError(
                "folder_id is required."
            )

        sql = """
            DELETE FROM public.document_chunks

            WHERE user_id = %s
              AND folder_id = %s
        """

        with self.pool.connection() as connection:

            with connection.cursor() as cursor:

                cursor.execute(
                    sql,
                    (
                        user_id,
                        folder_id,
                    ),
                )

                deleted_chunks = (
                    cursor.rowcount
                )

            connection.commit()

        return deleted_chunks

    # ==================================================
    # GET INDEXED FILES
    # ==================================================

    def get_indexed_files(
        self,
        user_id: str,
        folder_id: str,
    ) -> dict:

        if not user_id:

            raise ValueError(
                "user_id is required for "
                "indexed files."
            )

        if not folder_id:

            raise ValueError(
                "folder_id is required for "
                "indexed files."
            )

        sql = """
            SELECT DISTINCT ON (file_id)
                file_id,
                file_name,
                path,
                mime_type,
                modified_time

            FROM public.document_chunks

            WHERE user_id = %s
              AND folder_id = %s

            ORDER BY
                file_id,
                chunk_id
        """

        with self.pool.connection() as connection:

            with connection.cursor() as cursor:

                cursor.execute(
                    sql,
                    (
                        user_id,
                        folder_id,
                    ),
                )

                rows = cursor.fetchall()

        indexed_files = {}

        for row in rows:

            indexed_files[
                row["file_id"]
            ] = {
                "file_name":
                    row["file_name"],

                "modified_time":
                    row["modified_time"],

                "path":
                    row["path"],

                "mime_type":
                    row["mime_type"],
            }

        return indexed_files

    # ==================================================
    # GET INDEXED FILE DETAILS
    # ==================================================

    def get_indexed_file(
        self,
        user_id: str,
        folder_id: str,
        file_id: str,
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

        sql = """
            SELECT
                file_id,
                file_name,
                path,
                mime_type,
                modified_time,

                COUNT(*) AS chunk_count

            FROM public.document_chunks

            WHERE user_id = %s
              AND folder_id = %s
              AND file_id = %s

            GROUP BY
                file_id,
                file_name,
                path,
                mime_type,
                modified_time
        """

        with self.pool.connection() as connection:

            with connection.cursor() as cursor:

                cursor.execute(
                    sql,
                    (
                        user_id,
                        folder_id,
                        file_id,
                    ),
                )

                return cursor.fetchone()

    # ==================================================
    # USER FILE COUNT
    # ==================================================

    def get_user_file_count(
        self,
        user_id: str,
    ) -> int:

        if not user_id:
            raise ValueError(
                "user_id is required."
            )

        sql = """
            SELECT COUNT(
                DISTINCT file_id
            ) AS total

            FROM public.document_chunks

            WHERE user_id = %s
        """

        with self.pool.connection() as connection:

            with connection.cursor() as cursor:

                cursor.execute(
                    sql,
                    (
                        user_id,
                    ),
                )

                row = cursor.fetchone()

        return int(
            row["total"]
        )

    # ==================================================
    # USER CHUNK COUNT
    # ==================================================

    def get_user_chunk_count(
        self,
        user_id: str,
    ) -> int:

        return self.count(
            user_id=user_id
        )

    # ==================================================
    # DELETE SPECIFIC CHUNKS
    # ==================================================

    def delete_chunks(
        self,
        ids: list[str],
        user_id: str,
    ):

        if not ids:
            return

        if not user_id:

            raise ValueError(
                "user_id is required."
            )

        sql = """
            DELETE FROM public.document_chunks

            WHERE user_id = %s
              AND id = ANY(%s)
        """

        with self.pool.connection() as connection:

            with connection.cursor() as cursor:

                cursor.execute(
                    sql,
                    (
                        user_id,
                        ids,
                    ),
                )

            connection.commit()

    # ==================================================
    # GET ADJACENT CHUNKS
    # ==================================================

    def get_adjacent_chunks(
        self,
        user_id: str,
        file_id: str,
        chunk_ids: list[int],
        radius: int = 1,
    ):

        if not user_id:

            raise ValueError(
                "user_id is required."
            )

        if not file_id:

            raise ValueError(
                "file_id is required."
            )

        if not chunk_ids:

            return {
                "ids": [],
                "documents": [],
                "metadatas": [],
            }

        if radius < 0:

            radius = 0

        # ------------------------------------------
        # BUILD TARGET CHUNK IDS
        # ------------------------------------------

        targets = set()

        for chunk_id in chunk_ids:

            chunk_id = int(
                chunk_id
            )

            for offset in range(
                -radius,
                radius + 1,
            ):

                target = (
                    chunk_id
                    + offset
                )

                if target >= 0:

                    targets.add(
                        target
                    )

        chunk_list = sorted(
            targets
        )

        if not chunk_list:

            return {
                "ids": [],
                "documents": [],
                "metadatas": [],
            }

        # ------------------------------------------
        # SAME USER + SAME FILE
        # ------------------------------------------

        sql = """
            SELECT
                id,
                content,
                file_id,
                file_name,
                folder_id,
                path,
                mime_type,
                chunk_id,
                user_id,
                modified_time

            FROM public.document_chunks

            WHERE user_id = %s
              AND file_id = %s
              AND chunk_id = ANY(%s)

            ORDER BY chunk_id
        """

        with self.pool.connection() as connection:

            with connection.cursor() as cursor:

                cursor.execute(
                    sql,
                    (
                        user_id,
                        file_id,
                        chunk_list,
                    ),
                )

                rows = cursor.fetchall()

        return {
            "ids": [
                row["id"]
                for row in rows
            ],

            "documents": [
                row["content"]
                for row in rows
            ],

            "metadatas": [
                {
                    "file_name":
                        row["file_name"],

                    "file_id":
                        row["file_id"],

                    "folder_id":
                        row["folder_id"],

                    "path":
                        row["path"],

                    "mime_type":
                        row["mime_type"],

                    "chunk_id":
                        row["chunk_id"],

                    "user_id":
                        row["user_id"],

                    "modified_time":
                        row["modified_time"],
                }
                for row in rows
            ],
        }