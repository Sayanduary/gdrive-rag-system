import io

import pymupdf
from PIL import Image
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

from app.services.lmstudio import LMStudioService


SUPPORTED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/jpg",
    "image/webp",
}


lmstudio = LMStudioService()


# ==================================================
# PDF
# ==================================================

def extract_pdf_page_text(
    page
) -> str:

    return (
        page.get_text("text")
        .strip()
    )


def page_needs_ocr(
    page,
    min_text_chars: int = 30
) -> bool:

    text = extract_pdf_page_text(
        page
    )

    return len(text) < min_text_chars


def render_pdf_page(
    page
) -> bytes:

    pixmap = page.get_pixmap(
        matrix=pymupdf.Matrix(2, 2),
        alpha=False
    )

    image = Image.frombytes(
        "RGB",
        (
            pixmap.width,
            pixmap.height
        ),
        pixmap.samples
    )

    buffer = io.BytesIO()

    image.save(
        buffer,
        format="PNG"
    )

    return buffer.getvalue()


def ocr_pdf_page(
    page,
    page_number: int
) -> str:

    print(
        f"Vision OCR: page "
        f"{page_number}"
    )

    image_bytes = render_pdf_page(
        page
    )

    text = lmstudio.ocr_image(
        image_bytes=image_bytes,
        mime_type="image/png"
    )

    return text.strip()


def extract_pdf_text(
    file_bytes: bytes
) -> str:

    document = pymupdf.open(
        stream=file_bytes,
        filetype="pdf"
    )

    pages = []

    total_pages = len(
        document
    )

    print(
        f"PDF pages: {total_pages}"
    )

    for page_number, page in enumerate(
        document,
        start=1
    ):

        text = extract_pdf_page_text(
            page
        )

        # ------------------------------------------
        # Normal text page
        # ------------------------------------------

        if not page_needs_ocr(page):

            print(
                f"Page {page_number}: "
                f"text extraction "
                f"({len(text)} chars)"
            )

            if text:

                pages.append(
                    f"PAGE {page_number}\n"
                    f"{text}"
                )

            continue

        # ------------------------------------------
        # Scanned/image page
        # ------------------------------------------

        print(
            f"Page {page_number}: "
            f"low text ({len(text)} chars)"
        )

        try:

            ocr_text = ocr_pdf_page(
                page=page,
                page_number=page_number
            )

            if ocr_text:

                pages.append(
                    f"PAGE {page_number}\n"
                    f"{ocr_text}"
                )

            elif text:

                # Preserve tiny native text if
                # OCR returned nothing.
                pages.append(
                    f"PAGE {page_number}\n"
                    f"{text}"
                )

        except Exception as error:

            print(
                f"OCR failed on page "
                f"{page_number}: {error}"
            )

            # Do not lose existing PDF text
            # if Vision OCR fails.
            if text:

                pages.append(
                    f"PAGE {page_number}\n"
                    f"{text}"
                )

    document.close()

    return "\n\n".join(
        pages
    ).strip()


# ==================================================
# IMAGE OCR
# ==================================================

def extract_image_text(
    file_bytes: bytes,
    mime_type: str
) -> str:

    print(
        "Using LM Studio Vision OCR..."
    )

    return lmstudio.ocr_image(
        image_bytes=file_bytes,
        mime_type=mime_type
    ).strip()


# ==================================================
# PPTX
# ==================================================

def extract_pptx_shape_text(
    shape
) -> list[str]:

    extracted = []

    # ------------------------------------------
    # Group
    # ------------------------------------------

    if shape.shape_type == (
        MSO_SHAPE_TYPE.GROUP
    ):

        for child in shape.shapes:

            extracted.extend(
                extract_pptx_shape_text(
                    child
                )
            )

        return extracted

    # ------------------------------------------
    # Text
    # ------------------------------------------

    if hasattr(
        shape,
        "text"
    ):

        text = (
            shape.text
            .strip()
        )

        if text:

            extracted.append(
                text
            )

    # ------------------------------------------
    # Image
    # ------------------------------------------

    if shape.shape_type == (
        MSO_SHAPE_TYPE.PICTURE
    ):

        try:

            image_bytes = (
                shape.image.blob
            )

            mime_type = (
                getattr(
                    shape.image,
                    "content_type",
                    None
                )
                or "image/png"
            )

            print(
                "Processing PPTX image "
                "with Vision..."
            )

            image_text = lmstudio.ocr_image(
                image_bytes=image_bytes,
                mime_type=mime_type
            )

            if image_text:

                extracted.append(
                    image_text.strip()
                )

        except Exception as error:

            print(
                f"PPTX image OCR error: "
                f"{error}"
            )

    return extracted


def extract_pptx_text(
    file_bytes: bytes
) -> str:

    presentation = Presentation(
        io.BytesIO(file_bytes)
    )

    slides = []

    for slide_number, slide in enumerate(
        presentation.slides,
        start=1
    ):

        slide_parts = []

        for shape in slide.shapes:

            slide_parts.extend(
                extract_pptx_shape_text(
                    shape
                )
            )

        if slide_parts:

            slides.append(
                f"SLIDE {slide_number}\n"
                +
                "\n".join(
                    slide_parts
                )
            )

    return "\n\n".join(
        slides
    ).strip()


# ==================================================
# MAIN PARSER
# ==================================================

def parse_file(
    file_bytes: bytes,
    file_name: str,
    mime_type: str
) -> str:

    print(
        f"Parsing: {file_name}"
    )

    print(
        f"MIME type: {mime_type}"
    )

    # ==================================================
    # PDF
    # ==================================================

    if mime_type == "application/pdf":

        text = extract_pdf_text(
            file_bytes
        )

        print(
            f"Final PDF text characters: "
            f"{len(text)}"
        )

        return text.strip()

    # ==================================================
    # IMAGE
    # ==================================================

    if mime_type in SUPPORTED_IMAGE_TYPES:

        text = extract_image_text(
            file_bytes=file_bytes,
            mime_type=mime_type
        )

        print(
            f"Vision OCR characters: "
            f"{len(text)}"
        )

        return text.strip()

    # ==================================================
    # PPTX
    # ==================================================

    if mime_type == (
        "application/vnd.openxmlformats-officedocument"
        ".presentationml.presentation"
    ):

        text = extract_pptx_text(
            file_bytes
        )

        print(
            f"PPTX text characters: "
            f"{len(text)}"
        )

        return text.strip()

    # ==================================================
    # UNSUPPORTED
    # ==================================================

    raise ValueError(
        f"Unsupported file type: "
        f"{mime_type}"
    )