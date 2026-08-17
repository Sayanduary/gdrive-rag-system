import io

from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly"
]


def get_drive_service(
    credentials_data: dict
):
    """
    Create a Google Drive service using the
    currently authenticated user's OAuth credentials.
    """

    if not credentials_data:
        raise ValueError(
            "Google credentials are missing."
        )

    credentials = Credentials(
        token=credentials_data.get(
            "token"
        ),
        refresh_token=credentials_data.get(
            "refresh_token"
        ),
        token_uri=credentials_data.get(
            "token_uri"
        ),
        client_id=credentials_data.get(
            "client_id"
        ),
        client_secret=credentials_data.get(
            "client_secret"
        ),
        scopes=credentials_data.get(
            "scopes"
        ),
    )

    return build(
        "drive",
        "v3",
        credentials=credentials
    )


def list_folder_items(
    service,
    folder_id: str
):
    """
    Return all immediate children of a
    Google Drive folder (including Shared Drives).
    """

    items = []

    page_token = None

    while True:

        response = service.files().list(
            q=(
                f"'{folder_id}' "
                "in parents and trashed = false"
            ),
            spaces="drive",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            fields=(
                "nextPageToken,"
                "files("
                "id,"
                "name,"
                "mimeType,"
                "size,"
                "modifiedTime"
                ")"
            ),
            pageSize=100,
            pageToken=page_token
        ).execute()

        items.extend(
            response.get(
                "files",
                []
            )
        )

        page_token = response.get(
            "nextPageToken"
        )

        if not page_token:
            break

    return items


def recursive_list_files(
    service,
    folder_id: str,
    current_path: str = ""
):
    """
    Recursively traverse a Google Drive folder.

    Returns all files found inside the folder
    and its subfolders.
    """

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

        # ------------------------------------------
        # Google Drive folder
        # ------------------------------------------

        if (
            item["mimeType"]
            == "application/vnd.google-apps.folder"
        ):

            nested_files = recursive_list_files(
                service,
                item["id"],
                item_path
            )

            all_files.extend(
                nested_files
            )

        # ------------------------------------------
        # Regular file
        # ------------------------------------------

        else:

            file_data = {
                "id": item["id"],
                "name": item["name"],
                "mimeType": item["mimeType"],
                "size": item.get(
                    "size"
                ),
                "modifiedTime": item.get(
                    "modifiedTime"
                ),
                "path": item_path,
            }

            all_files.append(
                file_data
            )

    return all_files


def download_file(
    service,
    file_id: str,
    mime_type: str = "",
) -> tuple[bytes, str]:
    """
    Download a Google Drive file or export Google Workspace docs/slides.

    Returns (file_bytes, effective_mime_type).
    """

    effective_mime = mime_type

    # Export Google Docs as PDF
    if mime_type == "application/vnd.google-apps.document":
        request = service.files().export_media(
            fileId=file_id,
            mimeType="application/pdf"
        )
        effective_mime = "application/pdf"

    # Export Google Slides as PDF
    elif mime_type == "application/vnd.google-apps.presentation":
        request = service.files().export_media(
            fileId=file_id,
            mimeType="application/pdf"
        )
        effective_mime = "application/pdf"

    # Export Google Sheets as CSV
    elif mime_type == "application/vnd.google-apps.spreadsheet":
        request = service.files().export_media(
            fileId=file_id,
            mimeType="text/csv"
        )
        effective_mime = "text/csv"

    # Standard binary file download
    else:
        request = service.files().get_media(
            fileId=file_id,
            supportsAllDrives=True
        )

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

    return file_buffer.getvalue(), effective_mime