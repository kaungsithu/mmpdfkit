"""OCR module for extracting text from scanned PDF images using Tesseract."""

import sys
from pathlib import Path
from typing import Any, Dict, List


def extract_and_ocr(pdf_path: Path, enable_ocr: bool = True) -> List[Dict[str, Any]]:
    """
    Extract text from a PDF using Tesseract OCR (scanned documents).

    Uses Myanmar (mya) + English (eng) language models for best coverage
    of Burmese documents. Tesseract must be installed on the system with
    the Myanmar language pack.

    System requirements:
        - tesseract-ocr (apt: tesseract-ocr, brew: tesseract)
        - Myanmar language data (apt: tesseract-ocr-mya)

    Args:
        pdf_path: Path to PDF file
        enable_ocr: If False, raises ValueError (user disabled OCR)

    Returns:
        List of per-page span lists: [[page0_spans], [page1_spans], ...]
        Each inner list contains span dicts matching pdf_inspector output format.

    Raises:
        ValueError: If enable_ocr is False
        ImportError: If pytesseract or pillow is not installed
        FileNotFoundError: If pdf_path does not exist
    """
    if not enable_ocr:
        raise ValueError("OCR disabled by user (--no-ocr or config)")

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        raise ImportError(
            "pytesseract and pillow are required for OCR. Install with: pip install mmpdfkit[ocr]\n"
            "Also ensure Tesseract is installed: https://tesseract-ocr.github.io/tessdoc/Installation.html"
        )

    import fitz

    # Determine available languages — prefer Myanmar + English, fall back to English only
    try:
        available = pytesseract.get_languages()
        lang = "mya+eng" if "mya" in available else "eng"
    except Exception:
        lang = "eng"

    doc = fitz.open(str(pdf_path))
    # Returns a list of per-page span lists: [[page0_spans], [page1_spans], ...]
    pages_spans: List[List[Dict[str, Any]]] = []

    try:
        for page_num, page in enumerate(doc):
            # Render page at 2x for better OCR accuracy
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

            # Run Tesseract with bounding box data
            try:
                data = pytesseract.image_to_data(
                    img,
                    lang=lang,
                    output_type=pytesseract.Output.DICT,
                )
            except Exception as e:
                print(f"Warning: OCR failed on page {page_num + 1}: {e}", file=sys.stderr)
                pages_spans.append([])
                continue

            page_spans: List[Dict[str, Any]] = []
            n = len(data["text"])
            for i in range(n):
                text = data["text"][i].strip()
                conf = int(data["conf"][i])

                if not text or conf < 10:
                    continue

                # Convert image coords to PDF coords (undo 2x zoom)
                x0 = data["left"][i] / 2
                y0 = data["top"][i] / 2
                x1 = (data["left"][i] + data["width"][i]) / 2
                y1 = (data["top"][i] + data["height"][i]) / 2

                page_spans.append(
                    {
                        "text": text,
                        "font_name": "ocr",
                        "font_encoding": "unknown",
                        "font_size": 12.0,
                        "is_bold": False,
                        "is_italic": False,
                        "bbox": [x0, y0, x1, y1],
                    }
                )
            pages_spans.append(page_spans)
    finally:
        doc.close()

    return pages_spans
