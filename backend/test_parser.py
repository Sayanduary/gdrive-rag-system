from pathlib import Path

from app.services.parser import parse_file


PDF_PATH = Path(
    "data/downloads/Chapter-VI_Leave_Rules.pdf"
)


def main():

    print(
        f"Reading: {PDF_PATH}"
    )

    file_bytes = PDF_PATH.read_bytes()

    print(
        f"File size: {len(file_bytes)} bytes"
    )

    text = parse_file(
        file_bytes=file_bytes,
        file_name=PDF_PATH.name,
        mime_type="application/pdf"
    )

    print()
    print("=" * 70)
    print("EXTRACTED TEXT")
    print("=" * 70)

    print(
        text[:5000]
    )

    print()
    print("=" * 70)
    print(
        f"Total extracted characters: {len(text)}"
    )
    print("=" * 70)


if __name__ == "__main__":
    main()