import io

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleAuthRequest
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError

from config import settings


SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly"
]


# ============================================================
# CREATE DRIVE SERVICE
# ============================================================

def get_drive_service(
    credentials_data: dict
):
    """
    Create a Google Drive API service using the currently
    authenticated user's OAuth credentials.

    The session stores only ``token`` and ``refresh_token``
    to keep the cookie under 4 KB.  Static OAuth config
    (``token_uri``, ``client_id``, ``client_secret``) is
    reconstructed from server-side settings.

    Automatically refreshes an expired access token when a
    refresh token is available.
    """

    if not credentials_data:
        raise ValueError(
            "Google credentials are missing."
        )

    token = credentials_data.get("token")
    refresh_token = credentials_data.get("refresh_token")

    # ----------------------------------------------------------
    # Reconstruct static OAuth config from settings.
    #
    # The session cookie intentionally stores ONLY
    # token + refresh_token to stay under the 4 KB
    # browser cookie limit.
    #
    # Fall back to values stored in the session for
    # backwards compatibility with existing sessions.
    # ----------------------------------------------------------

    token_uri = (
        credentials_data.get("token_uri")
        or "https://oauth2.googleapis.com/token"
    )

    client_id = (
        credentials_data.get("client_id")
        or settings.GOOGLE_CLIENT_ID
    )

    client_secret = (
        credentials_data.get("client_secret")
        or settings.GOOGLE_CLIENT_SECRET
    )

    scopes = (
        credentials_data.get("scopes")
        or SCOPES
    )

    if not token:
        raise ValueError(
            "Google access token is missing."
        )

    credentials = Credentials(
        token=token,
        refresh_token=refresh_token,
        token_uri=token_uri,
        client_id=client_id,
        client_secret=client_secret,
        scopes=scopes,
    )

    # --------------------------------------------------------
    # Refresh expired access token
    # --------------------------------------------------------

    if credentials.expired:

        if not credentials.refresh_token:

            raise ValueError(
                "Google access token has expired and "
                "no refresh token is available. "
                "Please login with Google again."
            )

        print(
            "Google access token expired. Refreshing..."
        )

        credentials.refresh(
            GoogleAuthRequest()
        )

        print(
            "Google access token refreshed."
        )

    # --------------------------------------------------------
    # Build Drive API
    # --------------------------------------------------------

    service = build(
        "drive",
        "v3",
        credentials=credentials,
        cache_discovery=False,
    )

    return service


# ============================================================
# GET FOLDER INFORMATION
# ============================================================

def get_folder(
    service,
    folder_id: str
):
    """
    Verify that the authenticated Google account can access
    the requested folder.

    Returns folder metadata.
    """

    if not folder_id:
        raise ValueError(
            "Folder ID is empty."
        )

    print()
    print("=" * 70)
    print("VERIFYING GOOGLE DRIVE FOLDER")
    print("=" * 70)

    print(
        "Folder ID:",
        folder_id
    )

    try:

        folder = (
            service.files()
            .get(
                fileId=folder_id,

                fields=(
                    "id,"
                    "name,"
                    "mimeType,"
                    "trashed,"
                    "parents,"
                    "driveId,"
                    "webViewLink"
                ),

                supportsAllDrives=True,
            )
            .execute()
        )

    except HttpError as error:

        print()
        print(
            "GOOGLE DRIVE FOLDER VERIFICATION FAILED"
        )

        print(
            "HTTP status:",
            error.resp.status
        )

        print(
            "Error:",
            error
        )

        if error.resp.status == 404:

            raise ValueError(
                "Google Drive folder was not found or "
                "the currently authenticated Google account "
                "does not have access to it. "
                f"Folder ID: {folder_id}"
            )

        if error.resp.status == 403:

            raise ValueError(
                "The currently authenticated Google account "
                "does not have permission to access this folder."
            )

        raise

    # --------------------------------------------------------
    # Verify it really is a folder
    # --------------------------------------------------------

    if folder.get("mimeType") != (
        "application/vnd.google-apps.folder"
    ):

        raise ValueError(
            "The supplied Google Drive ID is not a folder. "
            f"Name: {folder.get('name')}"
        )

    if folder.get("trashed"):

        raise ValueError(
            "The Google Drive folder is in the trash."
        )

    print(
        "Folder name:",
        folder.get("name")
    )

    print(
        "Folder MIME:",
        folder.get("mimeType")
    )

    print(
        "Drive ID:",
        folder.get("driveId")
    )

    print(
        "Parents:",
        folder.get("parents")
    )

    print(
        "Web URL:",
        folder.get("webViewLink")
    )

    print(
        "Folder access: OK"
    )

    print("=" * 70)

    return folder


# ============================================================
# LIST FOLDER ITEMS
# ============================================================

def list_folder_items(
    service,
    folder_id: str
):
    """
    Return all immediate children of a Google Drive folder.

    Supports both:
    - My Drive
    - Shared Drives
    """

    # --------------------------------------------------------
    # First verify the folder
    # --------------------------------------------------------

    folder = get_folder(
        service,
        folder_id
    )

    drive_id = folder.get(
        "driveId"
    )

    items = []

    page_token = None

    # --------------------------------------------------------
    # Build common parameters
    # --------------------------------------------------------

    list_kwargs = {
        "q": (
            f"'{folder_id}' "
            "in parents and trashed = false"
        ),

        "spaces": "drive",

        "supportsAllDrives": True,

        "includeItemsFromAllDrives": True,

        "fields": (
            "nextPageToken,"
            "files("
            "id,"
            "name,"
            "mimeType,"
            "size,"
            "modifiedTime,"
            "driveId"
            ")"
        ),

        "pageSize": 100,
    }

    # --------------------------------------------------------
    # Shared Drive
    # --------------------------------------------------------

    if drive_id:

        print(
            "Folder belongs to Shared Drive:",
            drive_id
        )

        list_kwargs["corpora"] = "drive"
        list_kwargs["driveId"] = drive_id

    # --------------------------------------------------------
    # Fetch pages
    # --------------------------------------------------------

    while True:

        if page_token:

            list_kwargs["pageToken"] = page_token

        response = (
            service.files()
            .list(
                **list_kwargs
            )
            .execute()
        )

        page_items = response.get(
            "files",
            []
        )

        print(
            f"Drive returned {len(page_items)} "
            f"items."
        )

        items.extend(
            page_items
        )

        page_token = response.get(
            "nextPageToken"
        )

        if not page_token:

            break

    print(
        "Total immediate children:",
        len(items)
    )

    return items


# ============================================================
# RECURSIVE FILE LIST
# ============================================================

def recursive_list_files(
    service,
    folder_id: str,
    current_path: str = ""
):
    """
    Recursively traverse a Google Drive folder.

    Returns all files found inside the folder and
    all nested subfolders.
    """

    print()
    print(
        "Scanning folder:",
        folder_id
    )

    all_files = []

    items = list_folder_items(
        service,
        folder_id
    )

    for item in items:

        item_path = (
            f"{current_path}/{item['name']}"
            if current_path
            else item["name"]
        )

        mime_type = item.get(
            "mimeType"
        )

        # ----------------------------------------------------
        # Folder
        # ----------------------------------------------------

        if mime_type == (
            "application/vnd.google-apps.folder"
        ):

            print(
                "Entering subfolder:",
                item["name"]
            )

            nested_files = recursive_list_files(
                service,
                item["id"],
                item_path
            )

            all_files.extend(
                nested_files
            )

        # ----------------------------------------------------
        # Regular file
        # ----------------------------------------------------

        else:

            print(
                "Found file:",
                item["name"]
            )

            file_data = {
                "id": item["id"],
                "name": item["name"],
                "mimeType": mime_type,
                "size": item.get("size"),
                "modifiedTime": item.get(
                    "modifiedTime"
                ),
                "path": item_path,
                "driveId": item.get(
                    "driveId"
                ),
            }

            all_files.append(
                file_data
            )

    return all_files


# ============================================================
# DOWNLOAD FILE
# ============================================================

def download_file(
    service,
    file_id: str,
    mime_type: str = "",
) -> tuple[bytes, str]:
    """
    Download a Google Drive file or export Google Workspace
    documents.

    Returns:
        (file_bytes, effective_mime_type)
    """

    if not file_id:
        raise ValueError(
            "File ID is empty."
        )

    effective_mime = mime_type

    # --------------------------------------------------------
    # Google Docs -> PDF
    # --------------------------------------------------------

    if mime_type == (
        "application/vnd.google-apps.document"
    ):

        print(
            "Exporting Google Doc as PDF..."
        )

        request = (
            service.files()
            .export_media(
                fileId=file_id,
                mimeType="application/pdf"
            )
        )

        effective_mime = (
            "application/pdf"
        )

    # --------------------------------------------------------
    # Google Slides -> PDF
    # --------------------------------------------------------

    elif mime_type == (
        "application/vnd.google-apps.presentation"
    ):

        print(
            "Exporting Google Slides as PDF..."
        )

        request = (
            service.files()
            .export_media(
                fileId=file_id,
                mimeType="application/pdf"
            )
        )

        effective_mime = (
            "application/pdf"
        )

    # --------------------------------------------------------
    # Google Sheets -> CSV
    # --------------------------------------------------------

    elif mime_type == (
        "application/vnd.google-apps.spreadsheet"
    ):

        print(
            "Exporting Google Sheet as CSV..."
        )

        request = (
            service.files()
            .export_media(
                fileId=file_id,
                mimeType="text/csv"
            )
        )

        effective_mime = "text/csv"

    # --------------------------------------------------------
    # Normal file
    # --------------------------------------------------------

    else:

        print(
            "Downloading binary file:",
            file_id
        )

        request = (
            service.files()
            .get_media(
                fileId=file_id,
                supportsAllDrives=True
            )
        )

    # --------------------------------------------------------
    # Download
    # --------------------------------------------------------

    file_buffer = io.BytesIO()

    downloader = MediaIoBaseDownload(
        file_buffer,
        request,
        chunksize=1024 * 1024
    )

    done = False

    while not done:

        status, done = (
            downloader.next_chunk()
        )

        if status:

            print(
                "Download progress: "
                f"{status.progress() * 100:.1f}%"
            )

    file_bytes = (
        file_buffer.getvalue()
    )

    print(
        "Downloaded bytes:",
        len(file_bytes)
    )

    return (
        file_bytes,
        effective_mime
    )