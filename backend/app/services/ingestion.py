from app.services.gdrive import (
    recursive_list_files,
    download_file,
)

from app.services.parser import parse_file
from app.services.chunker import chunk_text
from app.services.vectorstore import VectorStore


SUPPORTED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/jpg",
    "image/webp",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


class IngestionService:

    def __init__(
        self,
        drive_service,
        user_id: str,
    ):

        if not user_id:
            raise ValueError(
                "user_id is required for ingestion."
            )

        self.drive_service = drive_service
        self.user_id = user_id

        self.vector_store = VectorStore()

    # ==================================================
    # INGEST FOLDER
    # ==================================================

    def ingest_folder(
        self,
        folder_id: str,
    ):

        if not folder_id:
            raise ValueError(
                "folder_id is required."
            )

        print()
        print("=" * 70)
        print("GOOGLE DRIVE ANALYSIS")
        print("=" * 70)

        print(
            f"User ID: {self.user_id}"
        )

        print(
            f"Folder ID: {folder_id}"
        )

        # --------------------------------------------------
        # Get current Drive files
        # --------------------------------------------------

        drive_files = recursive_list_files(
            self.drive_service,
            folder_id,
        )

        print(
            f"Files discovered in Drive: "
            f"{len(drive_files)}"
        )

        # --------------------------------------------------
        # Get indexed files for this user + folder
        # --------------------------------------------------

        indexed_files = (
            self.vector_store.get_indexed_files(
                user_id=self.user_id,
                folder_id=folder_id,
            )
        )

        print(
            f"Files currently indexed: "
            f"{len(indexed_files)}"
        )

        results = []

        drive_file_ids = set()

        # ==================================================
        # PROCESS DRIVE FILES
        # ==================================================

        for file in drive_files:

            file_id = file["id"]
            file_name = file["name"]
            mime_type = file["mimeType"]

            modified_time = file.get(
                "modifiedTime"
            )

            file_path = file.get(
                "path"
            )

            drive_file_ids.add(
                file_id
            )

            print()
            print("=" * 70)
            print(
                f"File: {file_name}"
            )
            print(
                f"Path: {file_path}"
            )
            print(
                f"File ID: {file_id}"
            )
            print(
                f"MIME Type: {mime_type}"
            )
            print(
                f"Modified: {modified_time}"
            )
            print("=" * 70)

            # --------------------------------------------------
            # Unsupported file
            # --------------------------------------------------

            if mime_type not in SUPPORTED_MIME_TYPES:

                print(
                    "SKIPPED: Unsupported file type."
                )

                results.append({
                    "file_id": file_id,
                    "file_name": file_name,
                    "status": "skipped",
                    "reason": "unsupported_file_type",
                })

                continue

            indexed_file = indexed_files.get(
                file_id
            )

            # ==================================================
            # EXISTING FILE
            # ==================================================

            if indexed_file:

                indexed_modified_time = (
                    indexed_file.get(
                        "modified_time"
                    )
                )

                # ------------------------------------------
                # Unchanged
                # ------------------------------------------

                if (
                    indexed_modified_time
                    == modified_time
                ):

                    print(
                        "UNCHANGED: Skipping."
                    )

                    results.append({
                        "file_id": file_id,
                        "file_name": file_name,
                        "status": "unchanged",
                    })

                    continue

                print(
                    "MODIFIED: Re-indexing file."
                )

            # ==================================================
            # DOWNLOAD + PARSE + CHUNK FIRST
            #
            # We intentionally do NOT delete the old chunks
            # yet. If parsing/OCR/embedding fails, the old
            # indexed version remains available.
            # ==================================================

            try:

                # ------------------------------------------
                # Download
                # ------------------------------------------

                print(
                    "Downloading file..."
                )

                file_bytes, effective_mime = download_file(
                    self.drive_service,
                    file_id,
                    mime_type=mime_type,
                )

                print(
                    f"Downloaded "
                    f"{len(file_bytes)} bytes"
                )

                # ------------------------------------------
                # Parse
                # ------------------------------------------

                text = parse_file(
                    file_bytes=file_bytes,
                    file_name=file_name,
                    mime_type=effective_mime,
                )

                print(
                    f"Extracted text: "
                    f"{len(text)} characters"
                )

                # ------------------------------------------
                # No text
                # ------------------------------------------

                if not text.strip():

                    print(
                        "No text extracted."
                    )

                    results.append({
                        "file_id": file_id,
                        "file_name": file_name,
                        "status": "failed",
                        "error": "No text extracted",
                    })

                    continue

                # ------------------------------------------
                # Chunk
                # ------------------------------------------

                chunks = chunk_text(
                    text
                )

                print(
                    f"Generated "
                    f"{len(chunks)} chunks"
                )

                if not chunks:

                    results.append({
                        "file_id": file_id,
                        "file_name": file_name,
                        "status": "failed",
                        "error": "No chunks generated",
                    })

                    continue

                # ------------------------------------------
                # Build IDs + metadata
                # ------------------------------------------

                ids = []
                metadatas = []

                for index, chunk in enumerate(
                    chunks
                ):

                    # Stable tenant/file/chunk ID.
                    chunk_id = (
                        f"{self.user_id}_"
                        f"{folder_id}_"
                        f"{file_id}_"
                        f"chunk_{index}"
                    )

                    ids.append(
                        chunk_id
                    )

                    metadatas.append({
                        "user_id":
                            self.user_id,

                        "folder_id":
                            folder_id,

                        "file_id":
                            file_id,

                        "file_name":
                            file_name,

                        "mime_type":
                            mime_type,

                        "modified_time":
                            modified_time,

                        "path":
                            file_path,

                        "chunk_id":
                            index,
                    })

                # ------------------------------------------
                # Generate embeddings + store in PostgreSQL
                # ------------------------------------------

                print(
                    "Generating embeddings..."
                )

                self.vector_store.add_documents(
                    texts=chunks,
                    metadatas=metadatas,
                    ids=ids,
                )

                # ------------------------------------------
                # Delete previous version ONLY after the
                # new chunks have successfully been stored.
                #
                # Because IDs are stable, this is mostly
                # relevant when chunk counts decrease.
                # ------------------------------------------

                if indexed_file:

                    print(
                        "Removing old chunks..."
                    )

                    # IMPORTANT:
                    # Delete all rows for this file first,
                    # then restore the newly generated chunks
                    # if the IDs overlap.
                    #
                    # But the PostgreSQL upsert above cannot
                    # remove stale old chunk IDs when the new
                    # version has fewer chunks.
                    #
                    # Therefore we remove stale chunks below
                    # using the current chunk count.

                    self._delete_stale_chunks(
                        file_id=file_id,
                        user_id=self.user_id,
                        folder_id=folder_id,
                        new_chunk_count=len(chunks),
                    )

                print(
                    "Successfully indexed in PostgreSQL."
                )

                results.append({
                    "file_id":
                        file_id,

                    "file_name":
                        file_name,

                    "status":
                        (
                            "modified"
                            if indexed_file
                            else "new"
                        ),

                    "chunks":
                        len(chunks),
                })

            except Exception as error:

                print(
                    f"ERROR: {error}"
                )

                results.append({
                    "file_id":
                        file_id,

                    "file_name":
                        file_name,

                    "status":
                        "failed",

                    "error":
                        str(error),
                })

        # ==================================================
        # DETECT DELETED DRIVE FILES
        # ==================================================

        deleted_files = []

        for file_id, file_info in (
            indexed_files.items()
        ):

            if file_id not in drive_file_ids:

                print()

                print(
                    f"DELETED FROM DRIVE: "
                    f"{file_info.get('file_name')}"
                )

                self.vector_store.delete_file(
                    file_id=file_id,
                    user_id=self.user_id,
                    folder_id=folder_id,
                )

                deleted_files.append({
                    "file_id":
                        file_id,

                    "file_name":
                        file_info.get(
                            "file_name"
                        ),

                    "status":
                        "deleted",
                })

        results.extend(
            deleted_files
        )

        # ==================================================
        # SUMMARY
        # ==================================================

        new_count = sum(
            1
            for item in results
            if item["status"] == "new"
        )

        modified_count = sum(
            1
            for item in results
            if item["status"] == "modified"
        )

        unchanged_count = sum(
            1
            for item in results
            if item["status"] == "unchanged"
        )

        deleted_count = sum(
            1
            for item in results
            if item["status"] == "deleted"
        )

        failed_count = sum(
            1
            for item in results
            if item["status"] == "failed"
        )

        skipped_count = sum(
            1
            for item in results
            if item["status"] == "skipped"
        )

        indexed_count = (
            self.vector_store.count(
                user_id=self.user_id,
                folder_id=folder_id,
            )
        )

        print()
        print("=" * 70)
        print("ANALYSIS SUMMARY")
        print("=" * 70)

        print(
            f"New:        {new_count}"
        )

        print(
            f"Modified:   {modified_count}"
        )

        print(
            f"Unchanged:  {unchanged_count}"
        )

        print(
            f"Deleted:    {deleted_count}"
        )

        print(
            f"Skipped:    {skipped_count}"
        )

        print(
            f"Failed:     {failed_count}"
        )

        print(
            f"Total chunks in current folder: "
            f"{indexed_count}"
        )

        print("=" * 70)

        return {
            "total_files":
                len(drive_files),

            "new":
                new_count,

            "modified":
                modified_count,

            "unchanged":
                unchanged_count,

            "deleted":
                deleted_count,

            "skipped":
                skipped_count,

            "failed":
                failed_count,

            "indexed_documents":
                indexed_count,

            "results":
                results,
        }

    # ==================================================
    # DELETE STALE CHUNKS
    # ==================================================

    def _delete_stale_chunks(
        self,
        file_id: str,
        user_id: str,
        folder_id: str,
        new_chunk_count: int,
    ):
        """
        Remove old chunk IDs when a modified file now
        produces fewer chunks than before.

        The current VectorStore API does not expose
        delete-by-chunk-id, so we retrieve the file's
        chunks and delete stale ones from PostgreSQL.
        """

        existing = (
            self.vector_store.get_file_chunks(
                file_id=file_id,
                user_id=user_id,
                folder_id=folder_id,
            )
        )

        existing_ids = existing.get(
            "ids",
            [],
        )

        stale_ids = []

        for index, vector_id in enumerate(
            existing_ids
        ):

            if index >= new_chunk_count:

                stale_ids.append(
                    vector_id
                )

        if not stale_ids:
            return

        self.vector_store.delete_chunks(
            ids=stale_ids,
            user_id=user_id,
        )