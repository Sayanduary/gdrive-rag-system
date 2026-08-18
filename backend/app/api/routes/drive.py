import re
import uuid
import threading

from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
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

ANALYSIS_JOBS = {}
ANALYSIS_JOBS_LOCK = threading.Lock()


# ==================================================
# REQUEST MODEL
# ==================================================

class DriveAnalyzeRequest(BaseModel):

    folder_url: str


# ==================================================
# SERVICES
# ==================================================

vector_store = VectorStore()

folder_service = AnalyzedFolderService()


# ==================================================
# EXTRACT FOLDER ID
# ==================================================

def extract_folder_id(
    folder_url: str,
) -> str:
    """
    Extract a Google Drive folder ID from:

    https://drive.google.com/drive/folders/FOLDER_ID
    https://drive.google.com/drive/u/1/folders/FOLDER_ID
    https://drive.google.com/drive/u/0/folders/FOLDER_ID
    https://drive.google.com/open?id=FOLDER_ID
    FOLDER_ID
    """

    if not isinstance(folder_url, str):

        raise ValueError(
            "Google Drive folder URL must be a string."
        )

    value = folder_url.strip()

    if not value:

        raise ValueError(
            "Google Drive folder URL cannot be empty."
        )

    # ==================================================
    # STANDARD /u/X/folders/ URL
    # ==================================================

    match = re.search(
        r"/folders/([a-zA-Z0-9\_-]+)",
        value,
    )

    if match:

        folder_id = match.group(1).strip()

        if folder_id:

            return folder_id

    # ==================================================
    # ?id=FOLDER_ID
    # ==================================================

    match = re.search(
        r"[?&]id=([a-zA-Z0-9\_-]+)",
        value,
    )

    if match:

        folder_id = match.group(1).strip()

        if folder_id:

            return folder_id

    # ==================================================
    # RAW FOLDER ID
    # ==================================================

    if re.fullmatch(
        r"[a-zA-Z0-9\_-]+",
        value,
    ):

        return value

    raise ValueError(
        "Invalid Google Drive folder URL. "
        "Expected a Google Drive folder link "
        "or folder ID."
    )


# ==================================================
# GOOGLE FOLDER METADATA
# ==================================================

def get_folder_metadata(
    drive_service,
    folder_id: str,
):
    """
    Verify that the authenticated Google account
    can access the requested Drive folder.
    """

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

        # ------------------------------------------
        # Make sure the returned object is actually
        # a folder.
        # ------------------------------------------

        mime_type = response.get(
            "mimeType"
        )

        if mime_type != (
            "application/vnd.google-apps.folder"
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    "The provided Google Drive ID "
                    "is not a folder."
                ),
            )

        return response

    except HTTPException:

        raise

    except Exception as error:

        print()
        print("=" * 70)
        print("GOOGLE DRIVE FOLDER ACCESS FAILED")
        print("=" * 70)

        print(
            f"Folder ID: {folder_id}"
        )

        print(
            f"Error type: "
            f"{type(error).__name__}"
        )

        print(
            f"Error: {error}"
        )

        print("=" * 70)

        # ------------------------------------------
        # Google Drive commonly returns 404 when:
        #
        # - folder doesn't exist
        # - folder isn't shared with this account
        # - authenticated account cannot access it
        # ------------------------------------------

        error_message = str(error)

        if (
            "404" in error_message
            or "File not found" in error_message
            or "notFound" in error_message
        ):

            raise HTTPException(
                status_code=404,
                detail=(
                    "Google Drive folder was not found "
                    "or the authenticated Google account "
                    "does not have access to it."
                ),
            )

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to access the Google Drive folder."
            ),
        )


# ==================================================
# DEBUG DRIVE ACCESS
# ==================================================

@router.get(
    "/debug/access/{folder_id}"
)
def debug_drive_access(
    folder_id: str,
    request: Request,
):
    """
    Debug whether the currently authenticated
    Google account can access a specific Drive folder.

    This does NOT perform ingestion.

    It only checks:
    1. Google user session
    2. Google credentials session
    3. Google Drive folder accessibility
    """

    print()
    print("=" * 70)
    print("DRIVE ACCESS DEBUG")
    print("=" * 70)

    # ==================================================
    # CURRENT GOOGLE USER
    # ==================================================

    user = request.session.get(
        "google_user"
    )

    print(
        "Authenticated user:",
        user
    )

    if not user:

        raise HTTPException(
            status_code=401,
            detail=(
                "No authenticated Google user."
            ),
        )

    # ==================================================
    # GOOGLE CREDENTIALS
    # ==================================================

    credentials_data = (
        request.session.get(
            "google_credentials"
        )
    )

    print(
        "Google credentials exist:",
        bool(credentials_data)
    )

    if not credentials_data:

        raise HTTPException(
            status_code=401,
            detail=(
                "No Google Drive credentials."
            ),
        )

    # ==================================================
    # FOLDER
    # ==================================================

    print(
        "Folder ID:",
        folder_id
    )

    # ==================================================
    # CREATE DRIVE SERVICE
    # ==================================================

    try:

        drive_service = get_drive_service(
            credentials_data
        )

        # ==================================================
        # VERIFY FOLDER
        # ==================================================

        folder = get_folder_metadata(
            drive_service,
            folder_id
        )

        print()
        print("DRIVE ACCESS: SUCCESS")

        print(
            "Folder name:",
            folder.get("name")
        )

        print(
            "Folder ID:",
            folder.get("id")
        )

        print(
            "MIME type:",
            folder.get("mimeType")
        )

        print(
            "Web URL:",
            folder.get("webViewLink")
        )

        print("=" * 70)

        return {
            "success": True,
            "user": user,
            "folder": folder,
        }

    except HTTPException:

        raise

    except Exception as error:

        print()
        print("=" * 70)
        print("DRIVE ACCESS DEBUG FAILED")
        print("=" * 70)

        print(
            "Error type:",
            type(error).__name__
        )

        print(
            "Error:",
            repr(error)
        )

        print("=" * 70)

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


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

    # ==================================================
    # FOLDER METADATA
    # ==================================================

    folder_metadata = get_folder_metadata(
        drive_service,
        folder_id,
    )

    folder_name = (
        folder_metadata.get("name")
        or "Google Drive Folder"
    )

    canonical_folder_url = (
        folder_metadata.get("webViewLink")
        or folder_url
    )

    # ==================================================
    # READ CURRENT INDEXED FILES
    # ==================================================

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

    # ==================================================
    # REMOVE STALE REGISTRY FILES
    # ==================================================

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

        if existing_file_id not in current_file_ids:

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

    # ==================================================
    # REGISTER CURRENT FILES
    # ==================================================

    total_chunks = 0

    registered_files = 0

    for file_id, metadata in (
        indexed_files.items()
    ):

        file_name = (
            metadata.get("file_name")
            or "Unknown file"
        )

        file_path = metadata.get(
            "path"
        )

        mime_type = metadata.get(
            "mime_type"
        )

        modified_time = metadata.get(
            "modified_time"
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

            total_chunks += chunk_count

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

    # ==================================================
    # REGISTER FOLDER SUMMARY
    # ==================================================

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
# BACKGROUND ANALYSIS WORKER
# ==================================================

def _run_drive_analysis(
    job_id: str,
    credentials_data: dict,
    user_id: str,
    folder_id: str,
    folder_url: str,
):
    try:
        with ANALYSIS_JOBS_LOCK:
            ANALYSIS_JOBS[job_id]["progress"] = "Connecting to Google Drive..."

        drive_service = get_drive_service(credentials_data)

        with ANALYSIS_JOBS_LOCK:
            ANALYSIS_JOBS[job_id]["progress"] = "Analyzing and indexing documents..."

        ingestion = IngestionService(
            drive_service=drive_service,
            user_id=user_id,
            vector_store=vector_store,
        )

        result = ingestion.ingest_folder(folder_id)

        with ANALYSIS_JOBS_LOCK:
            ANALYSIS_JOBS[job_id]["progress"] = "Registering folder metadata..."

        registry_result = register_analyzed_folder(
            user_id=user_id,
            folder_id=folder_id,
            folder_url=folder_url,
            drive_service=drive_service,
        )

        response = {
            "success": True,
            "folder_id": folder_id,
            "folder_name": registry_result["folder_name"],
            "file_count": registry_result["file_count"],
            "chunk_count": registry_result["chunk_count"],
            **result,
        }

        with ANALYSIS_JOBS_LOCK:
            ANALYSIS_JOBS[job_id]["status"] = "completed"
            ANALYSIS_JOBS[job_id]["progress"] = "Analysis completed successfully."
            ANALYSIS_JOBS[job_id]["result"] = response

        print(f"BACKGROUND ANALYSIS JOB {job_id} COMPLETED SUCCESSFULLY")

    except Exception as error:
        print(f"BACKGROUND ANALYSIS JOB {job_id} FAILED: {error}")
        with ANALYSIS_JOBS_LOCK:
            ANALYSIS_JOBS[job_id]["status"] = "failed"
            ANALYSIS_JOBS[job_id]["error"] = str(error)


# ==================================================
# ANALYSIS JOB STATUS
# ==================================================

@router.get("/status/{job_id}")
def get_analysis_status(job_id: str):
    with ANALYSIS_JOBS_LOCK:
        job = ANALYSIS_JOBS.get(job_id)

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Analysis job not found.",
        )

    return job


# ==================================================
# ANALYZE DRIVE FOLDER
# ==================================================

@router.post("/analyze")
def analyze_drive(
    payload: DriveAnalyzeRequest,
    request: Request,
    background_tasks: BackgroundTasks,
):

    # ==================================================
    # GOOGLE USER
    # ==================================================

    user = request.session.get("google_user")

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User is not authenticated.",
        )

    user_id = user.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Google user ID is missing.",
        )

    # ==================================================
    # GOOGLE CREDENTIALS
    # ==================================================

    credentials_data = request.session.get("google_credentials")

    if not credentials_data:
        raise HTTPException(
            status_code=401,
            detail=(
                "Google Drive authorization is missing or expired. "
                "Please sign in with Google again."
            ),
        )

    # ==================================================
    # EXTRACT FOLDER ID
    # ==================================================

    try:
        folder_id = extract_folder_id(payload.folder_url)
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    # ==================================================
    # VERIFY FOLDER ACCESS SYNCHRONOUSLY
    # ==================================================

    try:
        drive_service = get_drive_service(credentials_data)
        folder_metadata = get_folder_metadata(drive_service, folder_id)
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to access Google Drive folder: {error}",
        )

    # Store active folder ID in session
    request.session["active_folder_id"] = folder_id

    # ==================================================
    # CREATE BACKGROUND JOB
    # ==================================================

    job_id = uuid.uuid4().hex

    with ANALYSIS_JOBS_LOCK:
        ANALYSIS_JOBS[job_id] = {
            "status": "processing",
            "progress": "Connecting to Google Drive...",
            "result": None,
            "error": None,
            "folder_id": folder_id,
            "folder_name": folder_metadata.get("name"),
        }

    background_tasks.add_task(
        _run_drive_analysis,
        job_id=job_id,
        credentials_data=credentials_data,
        user_id=user_id,
        folder_id=folder_id,
        folder_url=payload.folder_url,
    )

    return {
        "status": "processing",
        "job_id": job_id,
        "folder_id": folder_id,
        "folder_name": folder_metadata.get("name"),
    }