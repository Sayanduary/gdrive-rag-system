from app.services.gdrive import (
    get_drive_service,
    recursive_list_files,
)


FOLDER_ID ="1euIpp64H6kJ3F0ibldIcdcQ0xMht8WVJ"


def main():

    service = get_drive_service()

    files = recursive_list_files(
        service,
        FOLDER_ID
    )

    print()
    print(f"Found {len(files)} files")
    print()

    for file in files:

        print(f"Name: {file['name']}")
        print(f"ID: {file['id']}")
        print(f"MIME Type: {file['mimeType']}")
        print(f"Path: {file['path']}")
        print("-" * 60)


if __name__ == "__main__":
    main()