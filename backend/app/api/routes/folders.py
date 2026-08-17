from fastapi import APIRouter, HTTPException, Request

from app.services.analyzed_folders import (
    AnalyzedFolderService,
)


router = APIRouter(
    prefix="/api/folders",
    tags=["Analyzed Folders"],
)


folder_service = AnalyzedFolderService()


def get_user_id(
    request: Request,
) -> str:

    user = request.session.get(
        "google_user"
    )

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

    return user_id


# ==================================================
# GET ALL ANALYZED FOLDERS
# ==================================================

@router.get("")
def list_analyzed_folders(
    request: Request,
):
    user_id = get_user_id(request)

    folders = (
        folder_service.get_user_folders(
            user_id
        )
    )

    return {
        "folders": folders
    }


# ==================================================
# GET ONE FOLDER
# ==================================================

@router.get("/{folder_id}")
def get_analyzed_folder(
    folder_id: str,
    request: Request,
):
    user_id = get_user_id(request)

    folder = (
        folder_service.get_folder(
            user_id,
            folder_id,
        )
    )

    if not folder:
        raise HTTPException(
            status_code=404,
            detail="Analyzed folder not found.",
        )

    files = (
        folder_service.get_folder_files(
            user_id,
            folder_id,
        )
    )

    return {
        "folder": folder,
        "files": files,
    }


# ==================================================
# GET FOLDER FILES
# ==================================================

@router.get("/{folder_id}/files")
def list_folder_files(
    folder_id: str,
    request: Request,
):
    user_id = get_user_id(request)

    folder = (
        folder_service.get_folder(
            user_id,
            folder_id,
        )
    )

    if not folder:
        raise HTTPException(
            status_code=404,
            detail="Analyzed folder not found.",
        )

    files = (
        folder_service.get_folder_files(
            user_id,
            folder_id,
        )
    )

    return {
        "folder": folder,
        "files": files,
    }


# ==================================================
# DELETE FILE FROM INDEX
# ==================================================

@router.delete("/{folder_id}/files/{file_id}")
def delete_analyzed_file(
    folder_id: str,
    file_id: str,
    request: Request,
):
    user_id = get_user_id(request)

    result = (
        folder_service.delete_file(
            user_id=user_id,
            folder_id=folder_id,
            file_id=file_id,
        )
    )

    if not result["deleted_file"]:
        raise HTTPException(
            status_code=404,
            detail="Analyzed file not found.",
        )

    if (
        request.session.get(
            "active_folder_id"
        )
        == folder_id
    ):
        # Keep the folder active if it still exists.
        request.session[
            "active_folder_id"
        ] = folder_id

    return {
        "success": True,
        **result,
    }


# ==================================================
# DELETE ANALYZED FOLDER
# ==================================================

@router.delete("/{folder_id}")
def delete_analyzed_folder(
    folder_id: str,
    request: Request,
):
    user_id = get_user_id(request)

    result = (
        folder_service.delete_folder(
            user_id=user_id,
            folder_id=folder_id,
        )
    )

    if not result["deleted_folder"]:
        raise HTTPException(
            status_code=404,
            detail="Analyzed folder not found.",
        )

    # Clear active session folder if this
    # was the current one.

    if (
        request.session.get(
            "active_folder_id"
        )
        == folder_id
    ):
        request.session.pop(
            "active_folder_id",
            None,
        )

    return {
        "success": True,
        **result,
    }