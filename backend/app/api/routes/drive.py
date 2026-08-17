import re

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.services.gdrive import get_drive_service
from app.services.ingestion import IngestionService
from app.services.vectorstore import VectorStore
from app.services.analyzed_folders import (
    AnalyzedFolderService,
)


router = APIRouter(
    prefix="/api/drive",
    tags=["Google Drive"],
)


class DriveAnalyzeRequest(BaseModel):
    folder_url: str


# ==================================================
# SERVICES
# ==================================================

vector_store = VectorStore()

folder_service = (
    AnalyzedFolderService()
)


# ==================================================
# EXTRACT FOLDER ID
# ==================================================

def extract_folder_id(
    folder_url: str,
) -> str:

    folder_url = (
        folder_url.strip()
    )

    patterns = [
        r"/folders/([a-zA-Z0-9_-]+)",
        r"[?&]id=([a-zA-Z0-9_-]+)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            folder_url,
        )

        if match:
            return match.group(1)

    # ----------------------------------------------
    # User pasted folder ID directly
    # ----------------------------------------------

    if re.fullmatch(
        r"[a-zA-Z0-9_-]+",
        folder_url,
    ):
        return folder_url

    raise ValueError(
        "Invalid Google Drive folder URL. "
        "Expected a Google Drive folder link."
    )


# ==================================================
# GET GOOGLE FOLDER METADATA
# ==================================================

def get_folder_metadata(
    drive_service,
    folder_id: str,
):

    try:

        response = (
            drive_service.files()
            .get(
                fileId=folder_id,
                fields=(
                    "id,"
                    "name,"
                    "mimeType,"
                    "webViewLink"
                ),
                supportsAllDrives=True,
            )
            .execute()
        )

        return response

    except Exception as error:

        print(
            "Unable to fetch folder metadata:",
            error,
        )

        return {
            "id": folder_id,
            "name": "Google Drive Folder",
            "webViewLink": None,
            "mimeType": (
                "application/vnd.google-apps.folder"
            ),
        }


# ==================================================
# REGISTER ANALYZED FOLDER + FILES
# ==================================================

def register_analyzed_folder(
    *,
    user_id: str,
    folder_id: str,
    folder_url: str,
    drive_service,
):
    """
    Synchronize the dashboard registry with the
    current contents of document_chunks.

    document_chunks remains the RAG source of truth.

    analyzed_folders / analyzed_files are the
    persistent dashboard registry.
    """

    # ----------------------------------------------
    # Folder metadata
    # ----------------------------------------------

    folder_metadata = (
        get_folder_metadata(
            drive_service,
            folder_id,
        )
    )

    folder_name = (
        folder_metadata.get("name")
        or "Google Drive Folder"
    )

    canonical_folder_url = (
        folder_metadata.get(
            "webViewLink"
        )
        or folder_url
    )

    # ----------------------------------------------
    # Read current indexed files from VectorStore
    # ----------------------------------------------

    indexed_files = (
        vector_store.get_indexed_files(
            user_id=user_id,
            folder_id=folder_id,
        )
    )

    current_file_ids = set(
        indexed_files.keys()
    )

    print()
    print("=" * 70)
    print("SYNCING ANALYZED FOLDER REGISTRY")
    print("=" * 70)

    print(
        f"User ID: {user_id}"
    )

    print(
        f"Folder ID: {folder_id}"
    )

    print(
        f"Folder name: {folder_name}"
    )

    print(
        f"Indexed files: {len(indexed_files)}"
    )

    # ----------------------------------------------
    # Remove registry entries for files that are no
    # longer present in document_chunks.
    #
    # This handles Drive deletions.
    # ----------------------------------------------

    existing_files = (
        folder_service.get_folder_files(
            user_id=user_id,
            folder_id=folder_id,
        )
    )

    for existing_file in existing_files:

        existing_file_id = (
            existing_file["file_id"]
        )

        if (
            existing_file_id
            not in current_file_ids
        ):

            print(
                "Removing stale registry file:",
                existing_file_id,
            )

            try:

                folder_service.delete_file(
                    user_id=user_id,
                    folder_id=folder_id,
                    file_id=existing_file_id,
                )

            except Exception as error:

                print(
                    "Failed to remove stale "
                    f"registry file "
                    f"{existing_file_id}: "
                    f"{error}"
                )

    # ----------------------------------------------
    # Register every currently indexed file
    # ----------------------------------------------

    total_chunks = 0

    registered_files = 0

    for file_id, metadata in (
        indexed_files.items()
    ):

        file_name = (
            metadata.get(
                "file_name"
            )
            or "Unknown file"
        )

        file_path = (
            metadata.get(
                "path"
            )
        )

        mime_type = (
            metadata.get(
                "mime_type"
            )
        )

        modified_time = (
            metadata.get(
                "modified_time"
            )
        )

        try:

            chunk_count = (
                vector_store.count_file(
                    user_id=user_id,
                    folder_id=folder_id,
                    file_id=file_id,
                )
            )

            folder_service.upsert_file(
                user_id=user_id,
                folder_id=folder_id,
                file_id=file_id,
                file_name=file_name,
                path=file_path,
                mime_type=mime_type,
                modified_time=modified_time,
                chunk_count=chunk_count,
            )

            total_chunks += (
                chunk_count
            )

            registered_files += 1

            print(
                f"Registered: "
                f"{file_name} "
                f"({chunk_count} chunks)"
            )

        except Exception as error:

            print(
                "Failed to register file "
                f"{file_name}: "
                f"{error}"
            )

    # ----------------------------------------------
    # Register folder summary
    # ----------------------------------------------

    folder_service.upsert_folder(
        user_id=user_id,
        folder_id=folder_id,
        folder_name=folder_name,
        folder_url=canonical_folder_url,
        file_count=registered_files,
        chunk_count=total_chunks,
    )

    print(
        f"Folder registered: "
        f"{folder_name}"
    )

    print(
        f"Files registered: "
        f"{registered_files}"
    )

    print(
        f"Chunks registered: "
        f"{total_chunks}"
    )

    print("=" * 70)

    return {
        "folder_name": folder_name,
        "file_count": registered_files,
        "chunk_count": total_chunks,
    }


# ==================================================
# ANALYZE DRIVE FOLDER
# ==================================================

@router.post("/analyze")
def analyze_drive(
    payload: DriveAnalyzeRequest,
    request: Request,
):

    # ==================================================
    # GOOGLE AUTHENTICATION
    # ==================================================

    credentials_data = (
        request.session.get(
            "google_credentials"
        )
    )

    if not credentials_data:

        raise HTTPException(
            status_code=401,
            detail=(
                "User is not authenticated "
                "with Google."
            ),
        )

    # ==================================================
    # GOOGLE USER
    # ==================================================

    user = request.session.get(
        "google_user"
    )

    if not user:

        raise HTTPException(
            status_code=401,
            detail=(
                "Google user information is missing."
            ),
        )

    user_id = user.get(
        "sub"
    )

    if not user_id:

        raise HTTPException(
            status_code=401,
            detail=(
                "Google user ID is missing."
            ),
        )

    # ==================================================
    # EXTRACT FOLDER ID
    # ==================================================

    try:

        folder_id = (
            extract_folder_id(
                payload.folder_url
            )
        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    # ==================================================
    # ANALYZE / INGEST
    # ==================================================

    try:

        print()
        print("=" * 70)
        print("DRIVE ANALYSIS REQUEST")
        print("=" * 70)

        print(
            f"User ID: {user_id}"
        )

        print(
            f"Folder ID: {folder_id}"
        )

        print(
            f"Folder URL: "
            f"{payload.folder_url}"
        )

        # ----------------------------------------------
        # Create Google Drive service
        # ----------------------------------------------

        drive_service = (
            get_drive_service(
                credentials_data
            )
        )

        # ----------------------------------------------
        # Create ingestion service
        # ----------------------------------------------

        ingestion = IngestionService(
            drive_service=drive_service,
            user_id=user_id,
        )

        # ----------------------------------------------
        # Analyze folder
        # ----------------------------------------------

        result = (
            ingestion.ingest_folder(
                folder_id
            )
        )

        # ----------------------------------------------
        # Register analyzed folder/files
        #
        # document_chunks has already been updated
        # by the ingestion process at this point.
        # ----------------------------------------------

        registry_result = (
            register_analyzed_folder(
                user_id=user_id,
                folder_id=folder_id,
                folder_url=(
                    payload.folder_url
                ),
                drive_service=drive_service,
            )
        )

        # ----------------------------------------------
        # Store active folder in session
        # ----------------------------------------------

        request.session[
            "active_folder_id"
        ] = folder_id

        # ----------------------------------------------
        # Final response
        # ----------------------------------------------

        response = {
            "success": True,

            "folder_id": folder_id,

            "folder_name":
                registry_result[
                    "folder_name"
                ],

            "file_count":
                registry_result[
                    "file_count"
                ],

            "chunk_count":
                registry_result[
                    "chunk_count"
                ],

            **result,
        }

        print()
        print("=" * 70)
        print("DRIVE ANALYSIS COMPLETED")
        print("=" * 70)

        print(
            f"Folder: "
            f"{registry_result['folder_name']}"
        )

        print(
            f"Files: "
            f"{registry_result['file_count']}"
        )

        print(
            f"Chunks: "
            f"{registry_result['chunk_count']}"
        )

        print("=" * 70)

        return response

    except HTTPException:
        raise

    except Exception as error:

        print()
        print("=" * 70)
        print("DRIVE ANALYSIS ERROR")
        print("=" * 70)

        print(
            f"{type(error).__name__}: "
            f"{error}"
        )

        print("=" * 70)

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )