from pathlib import Path

import chromadb
from fastembed import TextEmbedding


BASE_DIR = Path(__file__).resolve().parents[2]

CHROMA_PATH = BASE_DIR / "data" / "chroma_db"

COLLECTION_NAME = "gdrive_documents"

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"


class VectorStore:

    def __init__(self):

        self.client = chromadb.PersistentClient(
            path=str(CHROMA_PATH)
        )

        self.embedding_model = TextEmbedding(
            model_name=EMBEDDING_MODEL
        )

        self.collection = (
            self.client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={
                    "hnsw:space": "cosine"
                }
            )
        )

    # ==================================================
    # ADD / UPDATE DOCUMENTS
    # ==================================================

    def add_documents(
        self,
        texts: list[str],
        metadatas: list[dict],
        ids: list[str]
    ):

        if not texts:
            return

        if len(texts) != len(metadatas):
            raise ValueError(
                "texts and metadatas length mismatch."
            )

        if len(texts) != len(ids):
            raise ValueError(
                "texts and ids length mismatch."
            )

        # ----------------------------------------------
        # Security check:
        # Every chunk must have a tenant identity.
        # ----------------------------------------------

        for metadata in metadatas:

            if not metadata.get("user_id"):
                raise ValueError(
                    "Every document chunk must contain user_id."
                )

            if not metadata.get("folder_id"):
                raise ValueError(
                    "Every document chunk must contain folder_id."
                )

        embeddings = list(
            self.embedding_model.embed(
                texts
            )
        )

        embeddings = [
            embedding.tolist()
            for embedding in embeddings
        ]

        self.collection.upsert(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    # ==================================================
    # BUILD REQUIRED TENANT FILTER
    # ==================================================

    def _tenant_filter(
        self,
        user_id: str,
        folder_id: str | None = None
    ) -> dict:

        if not user_id:
            raise ValueError(
                "user_id is required for Chroma access."
            )

        filters = [
            {
                "user_id": user_id
            }
        ]

        if folder_id:
            filters.append(
                {
                    "folder_id": folder_id
                }
            )

        if len(filters) == 1:
            return filters[0]

        return {
            "$and": filters
        }

    # ==================================================
    # SEARCH
    # ==================================================

    def search(
        self,
        query: str,
        top_k: int = 5,
        user_id: str | None = None,
        folder_id: str | None = None
    ):

        if not user_id:
            raise ValueError(
                "user_id is required for Chroma search."
            )

        if not query or not query.strip():
            return {
                "ids": [[]],
                "documents": [[]],
                "metadatas": [[]],
                "distances": [[]],
            }

        if top_k <= 0:
            top_k = 5

        where = self._tenant_filter(
            user_id=user_id,
            folder_id=folder_id
        )

        # ----------------------------------------------
        # Count only current user's scope
        # ----------------------------------------------

        scoped_documents = self.collection.get(
            where=where,
            include=[]
        )

        scoped_count = len(
            scoped_documents.get(
                "ids",
                []
            )
        )

        if scoped_count == 0:

            return {
                "ids": [[]],
                "documents": [[]],
                "metadatas": [[]],
                "distances": [[]],
            }

        top_k = min(
            top_k,
            scoped_count
        )

        # ----------------------------------------------
        # Embed query
        # ----------------------------------------------

        query_embedding = list(
            self.embedding_model.embed(
                [query]
            )
        )[0]

        # ----------------------------------------------
        # Chroma search
        # ----------------------------------------------

        return self.collection.query(
            query_embeddings=[
                query_embedding.tolist()
            ],
            n_results=top_k,
            where=where,
            include=[
                "documents",
                "metadatas",
                "distances"
            ]
        )

    # ==================================================
    # COUNT
    # ==================================================

    def count(
        self,
        user_id: str
    ) -> int:

        if not user_id:
            raise ValueError(
                "user_id is required for count."
            )

        where = self._tenant_filter(
            user_id=user_id
        )

        results = self.collection.get(
            where=where,
            include=[]
        )

        return len(
            results.get(
                "ids",
                []
            )
        )

    # ==================================================
    # GET FILE CHUNKS
    # ==================================================

    def get_file_chunks(
        self,
        file_id: str,
        user_id: str,
        folder_id: str
    ):

        if not user_id:
            raise ValueError(
                "user_id is required."
            )

        where = {
            "$and": [
                {
                    "file_id": file_id
                },
                {
                    "user_id": user_id
                },
                {
                    "folder_id": folder_id
                }
            ]
        }

        return self.collection.get(
            where=where,
            include=[
                "documents",
                "metadatas"
            ]
        )

    # ==================================================
    # CHECK FILE EXISTS
    # ==================================================

    def file_exists(
        self,
        file_id: str,
        user_id: str,
        folder_id: str
    ) -> bool:

        results = self.collection.get(
            where={
                "$and": [
                    {
                        "file_id": file_id
                    },
                    {
                        "user_id": user_id
                    },
                    {
                        "folder_id": folder_id
                    }
                ]
            },
            limit=1,
            include=[]
        )

        return bool(
            results.get(
                "ids",
                []
            )
        )

    # ==================================================
    # GET MODIFICATION TIME
    # ==================================================

    def get_file_modified_time(
        self,
        file_id: str,
        user_id: str,
        folder_id: str
    ):

        results = self.collection.get(
            where={
                "$and": [
                    {
                        "file_id": file_id
                    },
                    {
                        "user_id": user_id
                    },
                    {
                        "folder_id": folder_id
                    }
                ]
            },
            limit=1,
            include=[
                "metadatas"
            ]
        )

        metadatas = results.get(
            "metadatas",
            []
        )

        if not metadatas:
            return None

        return metadatas[0].get(
            "modified_time"
        )

    # ==================================================
    # DELETE FILE
    # ==================================================

    def delete_file(
        self,
        file_id: str,
        user_id: str,
        folder_id: str
    ):

        self.collection.delete(
            where={
                "$and": [
                    {
                        "file_id": file_id
                    },
                    {
                        "user_id": user_id
                    },
                    {
                        "folder_id": folder_id
                    }
                ]
            }
        )

    # ==================================================
    # GET INDEXED FILES
    # ==================================================

    def get_indexed_files(
        self,
        user_id: str,
        folder_id: str
    ):

        results = self.collection.get(
            where={
                "$and": [
                    {
                        "user_id": user_id
                    },
                    {
                        "folder_id": folder_id
                    }
                ]
            },
            include=[
                "metadatas"
            ]
        )

        indexed_files = {}

        for metadata in results.get(
            "metadatas",
            []
        ):

            if not metadata:
                continue

            file_id = metadata.get(
                "file_id"
            )

            if not file_id:
                continue

            indexed_files[file_id] = {
                "file_name":
                    metadata.get(
                        "file_name"
                    ),
                "modified_time":
                    metadata.get(
                        "modified_time"
                    ),
            }

        return indexed_files