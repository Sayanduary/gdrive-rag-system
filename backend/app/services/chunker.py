import re


def clean_text(
    text: str
) -> str:

    if not text:
        return ""

    # Normalize line endings.
    text = text.replace(
        "\r\n",
        "\n"
    ).replace(
        "\r",
        "\n"
    )

    # Normalize horizontal whitespace.
    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    # Remove excessive blank lines.
    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text.strip()


def find_boundary(
    text: str,
    start: int,
    target_end: int,
    chunk_size: int
) -> int:

    candidates = [
        # Paragraph boundary
        text.rfind(
            "\n\n",
            start,
            target_end
        ),

        # Regulation/list item boundaries
        text.rfind(
            "\n(i) ",
            start,
            target_end
        ),

        text.rfind(
            "\n(ii) ",
            start,
            target_end
        ),

        text.rfind(
            "\n(iii) ",
            start,
            target_end
        ),

        text.rfind(
            "\n(iv) ",
            start,
            target_end
        ),

        text.rfind(
            "\n(v) ",
            start,
            target_end
        ),

        text.rfind(
            "\n(vi) ",
            start,
            target_end
        ),

        text.rfind(
            "\n(vii) ",
            start,
            target_end
        ),

        # Sentence boundaries
        text.rfind(
            ". ",
            start,
            target_end
        ),

        text.rfind(
            "? ",
            start,
            target_end
        ),

        text.rfind(
            "! ",
            start,
            target_end
        ),

        text.rfind(
            "; ",
            start,
            target_end
        ),

        # Last resort: whitespace
        text.rfind(
            " ",
            start,
            target_end
        ),
    ]

    boundary = max(
        candidates
    )

    minimum_boundary = (
        start
        + int(chunk_size * 0.55)
    )

    if boundary < minimum_boundary:
        return target_end

    # Include the punctuation/space boundary.
    if (
        boundary < len(text)
        and text[boundary:boundary + 2]
        in {
            ". ",
            "? ",
            "! ",
            "; "
        }
    ):

        return boundary + 1

    return boundary


def build_overlap(
    text: str,
    chunk_start: int,
    chunk_end: int,
    overlap: int
) -> str:

    if overlap <= 0:
        return ""

    overlap_start = max(
        chunk_start,
        chunk_end - overlap
    )

    overlap_text = (
        text[
            overlap_start:chunk_end
        ]
        .strip()
    )

    return overlap_text


def chunk_text(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 150
) -> list[str]:

    if not text:
        return []

    if chunk_size <= 0:
        raise ValueError(
            "chunk_size must be greater than 0"
        )

    if chunk_overlap < 0:
        raise ValueError(
            "chunk_overlap cannot be negative"
        )

    if chunk_overlap >= chunk_size:
        raise ValueError(
            "chunk_overlap must be smaller than chunk_size"
        )

    text = clean_text(
        text
    )

    if not text:
        return []

    chunks = []

    start = 0
    text_length = len(text)

    while start < text_length:

        target_end = min(
            start + chunk_size,
            text_length
        )

        # ----------------------------------------------
        # Final chunk
        # ----------------------------------------------

        if target_end >= text_length:

            chunk = (
                text[start:text_length]
                .strip()
            )

            if chunk:
                chunks.append(
                    chunk
                )

            break

        # ----------------------------------------------
        # Find semantic boundary
        # ----------------------------------------------

        boundary = find_boundary(
            text=text,
            start=start,
            target_end=target_end,
            chunk_size=chunk_size
        )

        chunk = (
            text[start:boundary]
            .strip()
        )

        if chunk:
            chunks.append(
                chunk
            )

        # ----------------------------------------------
        # Move forward with overlap
        # ----------------------------------------------

        overlap_text = build_overlap(
            text=text,
            chunk_start=start,
            chunk_end=boundary,
            overlap=chunk_overlap
        )

        if overlap_text:

            overlap_start = (
                boundary
                - len(overlap_text)
            )

            next_start = max(
                overlap_start,
                start + 1
            )

        else:

            next_start = max(
                boundary,
                start + 1
            )

        start = next_start

    return chunks