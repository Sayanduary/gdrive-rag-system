from pathlib import Path

from app.services.parser import parse_file
from app.services.chunker import chunk_text
from app.services.vectorstore import VectorStore


PDF_PATH = Path(
    "data/downloads/Chapter-VI_Leave_Rules.pdf"
)

FILE_ID = "1nCe_WHI6-JD5uHXVzP5t8wFQQuRbsc6O"


def main():

    # ----------------------------------------
    # 1. Read downloaded PDF
    # ----------------------------------------

    file_bytes = PDF_PATH.read_bytes()

    # ----------------------------------------
    # 2. Extract text
    # ----------------------------------------

    text = parse_file(
        file_bytes=file_bytes,
        file_name=PDF_PATH.name,
        mime_type="application/pdf"
    )

    print(
        f"Extracted characters: {len(text)}"
    )

    # ----------------------------------------
    # 3. Chunk text
    # ----------------------------------------

    chunks = chunk_text(
        text,
        chunk_size=1000,
        chunk_overlap=150
    )

    print(
        f"Generated chunks: {len(chunks)}"
    )

    # ----------------------------------------
    # 4. Initialize ChromaDB
    # ----------------------------------------

    vector_store = VectorStore()

    # ----------------------------------------
    # 5. Create metadata and IDs
    # ----------------------------------------

    metadatas = []
    ids = []

    for index, chunk in enumerate(chunks):

        metadatas.append({
            "file_id": FILE_ID,
            "file_name": PDF_PATH.name,
            "chunk_id": index,
        })

        ids.append(
            f"{FILE_ID}_chunk_{index}"
        )

    # ----------------------------------------
    # 6. Generate embeddings + store
    # ----------------------------------------

    print("Generating embeddings...")

    vector_store.add_documents(
        texts=chunks,
        metadatas=metadatas,
        ids=ids
    )

    print(
        f"ChromaDB document count: "
        f"{vector_store.count()}"
    )

    # ----------------------------------------
    # 7. Test semantic search
    # ----------------------------------------

    query = (
        "How many days of earned leave "
        "can be encashed on retirement?"
    )

    print()
    print("Searching ChromaDB...")
    print()

    results = vector_store.search(
        query=query,
        top_k=5
    )

    documents = results.get(
        "documents",
        [[]]
    )[0]

    metadatas = results.get(
        "metadatas",
        [[]]
    )[0]

    # ----------------------------------------
    # 8. Display results
    # ----------------------------------------

    print("=" * 70)
    print("SEARCH RESULTS")
    print("=" * 70)

    for index, document in enumerate(
        documents
    ):

        metadata = metadatas[index]

        print()
        print(
            f"RESULT {index + 1}"
        )

        print(
            f"File: {metadata['file_name']}"
        )

        print(
            f"Chunk: {metadata['chunk_id']}"
        )

        print("-" * 70)

        print(
            document[:1000]
        )

        print("-" * 70)


if __name__ == "__main__":
    main()