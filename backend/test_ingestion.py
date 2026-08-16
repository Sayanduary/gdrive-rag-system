from app.services.ingestion import IngestionService


FOLDER_ID = "1euIpp64H6kJ3F0ibldIcdcQ0xMht8WVJ"


def main():

    ingestion = IngestionService()

    result = ingestion.ingest_folder(
        FOLDER_ID
    )

    print()
    print("=" * 70)
    print("INGESTION SUMMARY")
    print("=" * 70)

    print(
        f"Total files discovered: "
        f"{result['total_files']}"
    )

    print(
        f"New:        "
        f"{result['new']}"
    )

    print(
        f"Modified:   "
        f"{result['modified']}"
    )

    print(
        f"Unchanged:  "
        f"{result['unchanged']}"
    )

    print(
        f"Deleted:    "
        f"{result['deleted']}"
    )

    print(
        f"Skipped:    "
        f"{result['skipped']}"
    )

    print(
        f"Failed:     "
        f"{result['failed']}"
    )

    print(
        f"Total ChromaDB chunks: "
        f"{result['indexed_documents']}"
    )

    print()
    print("=" * 70)
    print("FILES")
    print("=" * 70)

    for item in result["results"]:

        status = item.get(
            "status",
            "unknown"
        )

        file_name = item.get(
            "file_name",
            "Unknown"
        )

        chunks = item.get(
            "chunks",
            "-"
        )

        print(
            f"{status.upper():10} "
            f"{file_name} "
            f"({chunks} chunks)"
        )

        error = item.get("error")

        if error:

            print(
                f"  Error: {error}"
            )


if __name__ == "__main__":
    main()