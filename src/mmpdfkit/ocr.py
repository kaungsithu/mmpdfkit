"""OCR module for extracting text from scanned PDF images."""

from pathlib import Path
from typing import Any, Dict, List


def extract_and_ocr(pdf_path: Path, enable_ocr: bool = True) -> List[Dict[str, Any]]:
    """
    Extract text from a PDF using PaddleOCR (scanned documents).

    Args:
        pdf_path: Path to PDF file
        enable_ocr: If False, raises ValueError (user disabled OCR)

    Returns:
        List of span dicts matching pdf_inspector output format:
        {
            "text": "extracted text",
            "font_name": "ocr",
            "font_encoding": "unknown",
            "font_size": 12.0,
            "is_bold": False,
            "is_italic": False,
            "bbox": [x0, y0, x1, y1]
        }

    Raises:
        ValueError: If enable_ocr is False
        ImportError: If paddleocr is not installed
        FileNotFoundError: If pdf_path does not exist
    """
    if not enable_ocr:
        raise ValueError("OCR disabled by user (--no-ocr or config)")

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    try:
        from paddleocr import PaddleOCR
    except ImportError:
        raise ImportError("paddleocr is required for OCR. Install with: pip install mmpdfkit[ocr]")

    import fitz

    # Initialize OCR with language support
    # Myanmar language may not always be available; fallback to default
    try:
        ocr = PaddleOCR(lang="mm")
    except ValueError:
        # Myanmar language not available; use default (English + multilingual)
        ocr = PaddleOCR()

    doc = fitz.open(str(pdf_path))
    all_spans: List[Dict[str, Any]] = []

    try:
        for page_num, page in enumerate(doc):
            # Convert page to image
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better OCR
            img_bytes = pix.tobytes("png")

            # Run OCR
            try:
                result = ocr.ocr(img_bytes, cls=True)
            except Exception as e:
                print(f"Warning: OCR failed on page {page_num + 1}: {e}")
                continue

            # Convert OCR output to spans
            if result:
                for line in result:
                    if not line:
                        continue
                    for word_info in line:
                        # word_info is (bbox, (text, confidence))
                        bbox_points, text_conf = word_info
                        text, confidence = text_conf

                        # Skip very low confidence
                        if confidence < 0.1:
                            continue

                        # Convert bbox from image coords to PDF coords
                        # bbox_points is [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                        xs = [p[0] for p in bbox_points]
                        ys = [p[1] for p in bbox_points]
                        x0, x1 = min(xs) / 2, max(xs) / 2  # Undo 2x zoom
                        y0, y1 = min(ys) / 2, max(ys) / 2

                        span = {
                            "text": text.strip(),
                            "font_name": "ocr",
                            "font_encoding": "unknown",
                            "font_size": 12.0,  # Estimated
                            "is_bold": False,
                            "is_italic": False,
                            "bbox": [x0, y0, x1, y1],
                        }
                        all_spans.append(span)
    finally:
        doc.close()

    return all_spans
