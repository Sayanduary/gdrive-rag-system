from pathlib import Path

from app.services.parser import parse_file
from app.services.chunker import chunk_text


PDF_PATH = Path(
    "data/downloads/Chapter-VI_Leave_Rules.pdf"
)


def main():

    file_bytes = PDF_PATH.read_bytes()

    text = parse_file(
        file_bytes=file_bytes,
        file_name=PDF_PATH.name,
        mime_type="application/pdf"
    )

    chunks = chunk_text(
        text,
        chunk_size=1000,
        chunk_overlap=150
    )

    print(
        f"Total characters: {len(text)}"
    )

    print(
        f"Total chunks: {len(chunks)}"
    )

    print()

    for index, chunk in enumerate(
        chunks[:3]
    ):

        print("=" * 70)
        print(f"CHUNK {index}")
        print("=" * 70)
        print(chunk)


if __name__ == "__main__":
    main()