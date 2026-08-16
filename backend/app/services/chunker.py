import re


def chunk_text(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 150
) -> list[str]:

    if not text:
        return []

    if chunk_overlap >= chunk_size:
        raise ValueError(
            "chunk_overlap must be smaller than chunk_size"
        )

    # Normalize excessive whitespace
    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    ).strip()

    chunks = []

    start = 0
    text_length = len(text)

    while start < text_length:

        target_end = min(
            start + chunk_size,
            text_length
        )

        # If this is the final chunk
        if target_end == text_length:
            chunk = text[start:target_end].strip()

            if chunk:
                chunks.append(chunk)

            break

        # Try to find a natural boundary
        boundary_candidates = [
            text.rfind("\n\n", start, target_end),
            text.rfind(". ", start, target_end),
            text.rfind("? ", start, target_end),
            text.rfind("! ", start, target_end),
            text.rfind("; ", start, target_end),
            text.rfind(" ", start, target_end),
        ]

        boundary = max(boundary_candidates)

        # Don't allow a very small chunk
        minimum_boundary = start + int(
            chunk_size * 0.5
        )

        if boundary < minimum_boundary:
            boundary = target_end

        chunk = text[start:boundary].strip()

        if chunk:
            chunks.append(chunk)

        # Maintain overlap
        next_start = max(
            boundary - chunk_overlap,
            start + 1
        )

        start = next_start

    return chunks