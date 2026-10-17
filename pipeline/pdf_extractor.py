from pathlib import Path
from io import BytesIO

import pymupdf as fitz
import pytesseract

from PIL import Image

from models import Page


pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Users\dhalil.bello\AppData\Local\Tesseract-OCR\tesseract.exe"
)


def extract_pages(
    pdf_path: Path,
    document_id: str,
    *,
    use_ocr: bool = True,
    ocr_language: str = "fra+eng",
    min_native_chars: int = 40,
    dpi: int = 250,
):

    pages = []

    with fitz.open(pdf_path) as pdf:

        for page_index, pdf_page in enumerate(pdf):

            page_number = page_index + 1

            native_text = (
                pdf_page.get_text("text") or ""
            )

            text = native_text

            is_weak = (
                len(native_text.strip())
                < min_native_chars
            )

            method = (
                "native"
                if native_text.strip()
                else "empty"
            )

            if use_ocr and is_weak:

                pixmap = pdf_page.get_pixmap(
                    dpi=dpi,
                    alpha=False
                )

                image = Image.open(
                    BytesIO(
                        pixmap.tobytes("png")
                    )
                )

                recognized_text = (
                    pytesseract
                    .image_to_string(
                        image,
                        lang=ocr_language
                    )
                )

                if recognized_text.strip():

                    text = recognized_text

                    method = "ocr"

            pages.append(
                Page(
                    document_id=document_id,
                    page_number=page_number,
                    text=text,
                    char_count=len(text),
                    extraction_method=method,
                    needs_ocr_review=(
                        is_weak
                        or method == "ocr"
                    )
                )
            )

    return pages