from pathlib import Path

from app.services.gdrive import (
    get_drive_service,
    download_file,
)


FILE_ID = "1nCe_WHI6-JD5uHXVzP5t8wFQQuRbsc6O"

OUTPUT_DIR = Path("data/downloads")
OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

OUTPUT_FILE = (
    OUTPUT_DIR
    / "Chapter-VI_Leave_Rules.pdf"
)


def main():

    service = get_drive_service()

    print("Downloading file...")

    file_bytes = download_file(
        service,
        FILE_ID
    )

    OUTPUT_FILE.write_bytes(
        file_bytes
    )

    print(
        f"Downloaded {len(file_bytes)} bytes"
    )

    print(
        f"Saved to: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()