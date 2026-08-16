import re

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.services.gdrive import get_drive_service
from app.services.ingestion import IngestionService


router = APIRouter(
    prefix="/api/drive",
    tags=["Google Drive"]
)


class DriveAnalyzeRequest(BaseModel):

    folder_url: str


def extract_folder_id(
    folder_url: str
) -> str:

    folder_url = folder_url.strip()

    patterns = [
        r"/folders/([a-zA-Z0-9_-]+)",
        r"[?&]id=([a-zA-Z0-9_-]+)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            folder_url
        )

        if match:
            return match.group(1)

    # User pasted the folder ID itself
    if re.fullmatch(
        r"[a-zA-Z0-9_-]+",
        folder_url
    ):
        return folder_url

    raise ValueError(
        "Invalid Google Drive folder URL. "
        "Expected a Google Drive folder link."
    )


@router.post("/analyze")
def analyze_drive(
    payload: DriveAnalyzeRequest,
    request: Request
):

    # ==================================================
    # GOOGLE AUTHENTICATION
    # ==================================================

    credentials_data = request.session.get(
        "google_credentials"
    )

    if not credentials_data:

        raise HTTPException(
            status_code=401,
            detail=(
                "User is not authenticated "
                "with Google."
            )
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
            )
        )

    user_id = user.get(
        "sub"
    )

    if not user_id:

        raise HTTPException(
            status_code=401,
            detail=(
                "Google user ID is missing."
            )
        )

    # ==================================================
    # EXTRACT FOLDER ID
    # ==================================================

    try:

        folder_id = extract_folder_id(
            payload.folder_url
        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
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

        # ----------------------------------------------
        # Create Drive service for this user
        # ----------------------------------------------

        drive_service = get_drive_service(
            credentials_data
        )

        # ----------------------------------------------
        # Pass user identity to ingestion
        # ----------------------------------------------

        ingestion = IngestionService(
            drive_service=drive_service,
            user_id=user_id
        )

        # ----------------------------------------------
        # Analyze folder
        # ----------------------------------------------

        result = ingestion.ingest_folder(
            folder_id
        )

        # ----------------------------------------------
        # Store active folder in session
        # ----------------------------------------------

        request.session[
            "active_folder_id"
        ] = folder_id

        return {
            "success": True,
            "folder_id": folder_id,
            **result
        }

    except Exception as error:

        print(
            f"DRIVE ANALYSIS ERROR: {error}"
        )

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )