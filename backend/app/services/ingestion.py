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
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


class IngestionService:

    def __init__(
        self,
        drive_service,
        user_id: str
    ):

        self.drive_service = drive_service

        self.user_id = user_id

        self.vector_store = VectorStore()

    # ==================================================
    # INGEST FOLDER
    # ==================================================

    def ingest_folder(
        self,
        folder_id: str
    ):

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
        # Get current files from Google Drive
        # --------------------------------------------------

        drive_files = recursive_list_files(
            self.drive_service,
            folder_id
        )

        print(
            f"Files discovered in Drive: "
            f"{len(drive_files)}"
        )

        # --------------------------------------------------
        # Get files already indexed for THIS USER +
        # THIS FOLDER
        # --------------------------------------------------

        indexed_files = (
            self.vector_store.get_indexed_files(
                user_id=self.user_id,
                folder_id=folder_id
            )
        )

        print(
            f"Files currently indexed: "
            f"{len(indexed_files)}"
        )

        results = []

        # Track Drive file IDs for deletion detection
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
                    "reason": "unsupported_file_type"
                })

                continue

            # --------------------------------------------------
            # Check existing indexed file
            # --------------------------------------------------

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
                        "status": "unchanged"
                    })

                    continue

                # ------------------------------------------
                # Modified
                # ------------------------------------------

                print(
                    "MODIFIED: Re-indexing file."
                )

                self.vector_store.delete_file(
                    file_id=file_id,
                    user_id=self.user_id,
                    folder_id=folder_id
                )

            # ==================================================
            # NEW OR MODIFIED FILE
            # ==================================================

            try:

                # ------------------------------------------
                # Download
                # ------------------------------------------

                print(
                    "Downloading file..."
                )

                file_bytes = download_file(
                    self.drive_service,
                    file_id
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
                    mime_type=mime_type
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
                        "No text extracted. "
                        "Skipping."
                    )

                    results.append({
                        "file_id": file_id,
                        "file_name": file_name,
                        "status": "failed",
                        "error": "No text extracted"
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
                        "error": "No chunks generated"
                    })

                    continue

                # ------------------------------------------
                # Metadata
                # ------------------------------------------

                ids = []

                metadatas = []

                for index, chunk in enumerate(
                    chunks
                ):

                    # Scope the Chroma ID by user +
                    # folder + Drive file.
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
                        "user_id": self.user_id,
                        "folder_id": folder_id,
                        "file_id": file_id,
                        "file_name": file_name,
                        "mime_type": mime_type,
                        "modified_time": modified_time,
                        "path": file_path,
                        "chunk_id": index,
                    })

                # ------------------------------------------
                # Embed + store
                # ------------------------------------------

                print(
                    "Generating embeddings..."
                )

                self.vector_store.add_documents(
                    texts=chunks,
                    metadatas=metadatas,
                    ids=ids
                )

                print(
                    "Successfully indexed."
                )

                results.append({
                    "file_id": file_id,
                    "file_name": file_name,
                    "status": (
                        "modified"
                        if indexed_file
                        else "new"
                    ),
                    "chunks": len(chunks)
                })

            except Exception as error:

                print(
                    f"ERROR: {error}"
                )

                results.append({
                    "file_id": file_id,
                    "file_name": file_name,
                    "status": "failed",
                    "error": str(error)
                })

        # ==================================================
        # DETECT DELETED FILES
        # ==================================================

        deleted_files = []

        for file_id, file_info in indexed_files.items():

            if file_id not in drive_file_ids:

                print()

                print(
                    f"DELETED FROM DRIVE: "
                    f"{file_info.get('file_name')}"
                )

                self.vector_store.delete_file(
                    file_id=file_id,
                    user_id=self.user_id,
                    folder_id=folder_id
                )

                deleted_files.append({
                    "file_id": file_id,
                    "file_name": file_info.get(
                        "file_name"
                    ),
                    "status": "deleted"
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
                folder_id=folder_id
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
            "total_files": len(
                drive_files
            ),
            "new": new_count,
            "modified": modified_count,
            "unchanged": unchanged_count,
            "deleted": deleted_count,
            "skipped": skipped_count,
            "failed": failed_count,
            "indexed_documents": indexed_count,
            "results": results
        }