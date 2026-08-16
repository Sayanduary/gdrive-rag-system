from app.services.gdrive import get_drive_service


def main():
    service = get_drive_service()

    response = service.files().list(
        pageSize=10,
        fields="files(id, name, mimeType)"
    ).execute()

    files = response.get("files", [])

    print("\nGoogle Drive connection successful!\n")

    if not files:
        print("No files found.")
        return

    for file in files:
        print(
            f"Name: {file['name']}"
        )
        print(
            f"ID: {file['id']}"
        )
        print(
            f"MIME Type: {file['mimeType']}"
        )
        print("-" * 50)


if __name__ == "__main__":
    main()