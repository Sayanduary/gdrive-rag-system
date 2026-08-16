from app.services.rag import RAGService


def main():

    rag = RAGService()

    question = (
    "What is an employee in permanent service?"
)

    print("Question:")
    print(question)

    print()
    print("Generating answer...")

    result = rag.query(
        question,
        top_k=5
    )

    print()
    print("=" * 70)
    print("ANSWER")
    print("=" * 70)

    print(
        result["answer"]
    )

    print()
    print("=" * 70)
    print("SOURCES")
    print("=" * 70)

    for source in result["sources"]:

        print(
            f"File: {source['file_name']}"
        )

        print(
            f"Chunk: {source['chunk_id']}"
        )

        print("-" * 50)


if __name__ == "__main__":
    main()