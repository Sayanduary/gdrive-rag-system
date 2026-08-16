import io
import zipfile

import pymupdf
import pytesseract

from PIL import Image, ImageOps, ImageEnhance
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE


SUPPORTED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/jpg",
}


# ============================================================
# OCR HELPERS
# ============================================================

def prepare_ocr_image(
    image: Image.Image
) -> Image.Image:
    """
    Prepare an image for better OCR accuracy.
    """

    image = image.convert("RGB")

    width, height = image.size

    # Upscale small images
    if width < 1600:

        scale = 1600 / width

        image = image.resize(
            (
                int(width * scale),
                int(height * scale)
            ),
            Image.Resampling.LANCZOS
        )

    # Grayscale
    image = ImageOps.grayscale(
        image
    )

    # Increase contrast
    image = ImageEnhance.Contrast(
        image
    ).enhance(1.5)

    return image


def ocr_image(
    image: Image.Image
) -> str:
    """
    OCR an image using Tesseract.
    """

    try:

        prepared = prepare_ocr_image(
            image
        )

        text = pytesseract.image_to_string(
            prepared,
            config="--psm 6"
        )

        return text.strip()

    except Exception as error:

        print(
            f"OCR error: {error}"
        )

        return ""


# ============================================================
# PDF TEXT
# ============================================================

def extract_pdf_text(
    file_bytes: bytes
) -> str:
    """
    Extract selectable text from PDF.
    """

    pdf_document = pymupdf.open(
        stream=file_bytes,
        filetype="pdf"
    )

    pages = []

    for page in pdf_document:

        text = page.get_text(
            "text"
        )

        if text:
            pages.append(
                text
            )

    pdf_document.close()

    return "\n".join(
        pages
    ).strip()


# ============================================================
# PDF OCR
# ============================================================

def extract_pdf_ocr(
    file_bytes: bytes
) -> str:
    """
    Render PDF pages and OCR them.
    """

    pdf_document = pymupdf.open(
        stream=file_bytes,
        filetype="pdf"
    )

    pages = []

    total_pages = len(
        pdf_document
    )

    for page_number, page in enumerate(
        pdf_document,
        start=1
    ):

        print(
            f"OCR processing page "
            f"{page_number}/{total_pages}"
        )

        pixmap = page.get_pixmap(
            matrix=pymupdf.Matrix(
                2,
                2
            ),
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

        text = ocr_image(
            image
        )

        if text:
            pages.append(
                text
            )

    pdf_document.close()

    return "\n".join(
        pages
    ).strip()


# ============================================================
# STANDALONE IMAGE OCR
# ============================================================

def extract_image_text(
    file_bytes: bytes
) -> str:
    """
    Extract text from standalone image.
    """

    image = Image.open(
        io.BytesIO(file_bytes)
    )

    return ocr_image(
        image
    )


# ============================================================
# PPTX DIRECT TEXT
# ============================================================

def extract_pptx_shape_text(
    shape
) -> list[str]:
    """
    Extract normal PowerPoint text recursively.
    """

    extracted = []

    # --------------------------------------------------------
    # Group
    # --------------------------------------------------------

    if shape.shape_type == MSO_SHAPE_TYPE.GROUP:

        for child in shape.shapes:

            extracted.extend(
                extract_pptx_shape_text(
                    child
                )
            )

        return extracted

    # --------------------------------------------------------
    # Text
    # --------------------------------------------------------

    if hasattr(
        shape,
        "text"
    ):

        text = shape.text.strip()

        if text:
            extracted.append(
                text
            )

    # --------------------------------------------------------
    # Direct image OCR
    # --------------------------------------------------------

    if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:

        try:

            print(
                "OCR processing PPTX image shape..."
            )

            image_blob = shape.image.blob

            image = Image.open(
                io.BytesIO(
                    image_blob
                )
            )

            text = ocr_image(
                image
            )

            if text:
                extracted.append(
                    text
                )

        except Exception as error:

            print(
                f"PPTX shape OCR error: {error}"
            )

    return extracted


# ============================================================
# PPTX EMBEDDED MEDIA OCR
# ============================================================

def extract_pptx_embedded_images(
    file_bytes: bytes
) -> list[str]:
    """
    Extract and OCR every image embedded inside
    the PPTX ZIP archive.

    This catches full-slide images and image-based
    presentation content that python-pptx may not
    expose as normal text.
    """

    extracted = []

    image_extensions = (
        ".png",
        ".jpg",
        ".jpeg",
        ".bmp",
        ".tif",
        ".tiff",
        ".webp",
    )

    try:

        with zipfile.ZipFile(
            io.BytesIO(file_bytes)
        ) as archive:

            media_files = [
                name
                for name in archive.namelist()
                if name.lower().startswith(
                    "ppt/media/"
                )
                and name.lower().endswith(
                    image_extensions
                )
            ]

            print(
                f"PPTX embedded images found: "
                f"{len(media_files)}"
            )

            for index, media_name in enumerate(
                media_files,
                start=1
            ):

                print(
                    f"OCR processing embedded "
                    f"PPTX image "
                    f"{index}/{len(media_files)}"
                )

                image_bytes = archive.read(
                    media_name
                )

                image = Image.open(
                    io.BytesIO(
                        image_bytes
                    )
                )

                text = ocr_image(
                    image
                )

                if text:
                    extracted.append(
                        f"Embedded image: "
                        f"{media_name}\n"
                        f"{text}"
                    )

    except Exception as error:

        print(
            f"PPTX embedded media error: "
            f"{error}"
        )

    return extracted


# ============================================================
# PPTX TEXT + OCR
# ============================================================

def extract_pptx_text(
    file_bytes: bytes
) -> str:
    """
    Extract PowerPoint text and OCR embedded images.
    """

    presentation = Presentation(
        io.BytesIO(
            file_bytes
        )
    )

    slides = []

    # --------------------------------------------------------
    # Normal slide content
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Embedded image content
    # --------------------------------------------------------

    embedded_image_text = (
        extract_pptx_embedded_images(
            file_bytes
        )
    )

    if embedded_image_text:

        slides.append(
            "PPTX EMBEDDED IMAGE CONTENT\n"
            +
            "\n\n".join(
                embedded_image_text
            )
        )

    return "\n\n".join(
        slides
    ).strip()


# ============================================================
# MAIN PARSER
# ============================================================

def parse_file(
    file_bytes: bytes,
    file_name: str,
    mime_type: str
) -> str:
    """
    Detect file type and extract text.

    Supported:
        PDF
        JPEG
        PNG
        PPTX
    """

    print(
        f"Parsing: {file_name}"
    )

    print(
        f"MIME type: {mime_type}"
    )

    # ========================================================
    # PDF
    # ========================================================

    if mime_type == "application/pdf":

        text = extract_pdf_text(
            file_bytes
        )

        print(
            f"PDF text characters: "
            f"{len(text)}"
        )

        # OCR scanned or poorly extracted PDFs
        if len(text.strip()) < 500:

            print(
                "Detected scanned or poorly "
                "extracted PDF."
            )

            print(
                "Using Tesseract OCR..."
            )

            text = extract_pdf_ocr(
                file_bytes
            )

            print(
                f"OCR text characters: "
                f"{len(text)}"
            )

        return text.strip()

    # ========================================================
    # IMAGE
    # ========================================================

    if mime_type in SUPPORTED_IMAGE_TYPES:

        print(
            "Processing image with "
            "Tesseract OCR..."
        )

        text = extract_image_text(
            file_bytes
        )

        print(
            f"OCR text characters: "
            f"{len(text)}"
        )

        return text.strip()

    # ========================================================
    # PPTX
    # ========================================================

    if (
        mime_type
        ==
        (
            "application/vnd.openxmlformats-officedocument"
            ".presentationml.presentation"
        )
    ):

        print(
            "Processing PowerPoint presentation..."
        )

        text = extract_pptx_text(
            file_bytes
        )

        print(
            f"PPTX extracted characters: "
            f"{len(text)}"
        )

        return text.strip()

    # ========================================================
    # UNSUPPORTED
    # ========================================================

    raise ValueError(
        f"Unsupported file type: "
        f"{mime_type}"
    )