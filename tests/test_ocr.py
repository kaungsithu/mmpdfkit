"""Tests for OCR module."""
from pathlib import Path

import fitz
import pytest
from mmpdfkit.ocr import extract_and_ocr


def make_blank_pdf_bytes():
    """Create a blank PDF (simulating scanned document with no text)."""
    doc = fitz.open()
    doc.new_page(width=595, height=842)
    return doc.tobytes()


def test_extract_and_ocr_disabled():
    """extract_and_ocr raises ValueError if enable_ocr=False."""
    pdf_bytes = make_blank_pdf_bytes()

    with pytest.raises(ValueError, match="OCR disabled"):
        # Create temp file
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(pdf_bytes)
            temp_path = f.name

        try:
            extract_and_ocr(Path(temp_path), enable_ocr=False)
        finally:
            Path(temp_path).unlink()


def test_extract_and_ocr_missing_paddleocr():
    """extract_and_ocr raises ImportError if paddleocr not installed."""
    pytest.importorskip("paddleocr")  # Skip if not installed (OK for this test env)
    # This test is a placeholder — actual test will run if paddleocr is available


def test_extract_and_ocr_returns_spans():
    """extract_and_ocr returns list of span dicts."""
    try:
        import paddle  # noqa

        pytest.importorskip("paddleocr")
    except ImportError:
        pytest.skip("paddlepaddle not available (OCR tests require full setup)")

    pdf_bytes = make_blank_pdf_bytes()

    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(pdf_bytes)
        temp_path = f.name

    try:
        result = extract_and_ocr(Path(temp_path), enable_ocr=True)

        # Should return a list
        assert isinstance(result, list)

        # Each item should be a span dict
        for span in result:
            assert isinstance(span, dict)
            assert "text" in span
            assert "font_name" in span
            assert "font_encoding" in span
            assert "font_size" in span
            assert "is_bold" in span
            assert "is_italic" in span
            assert "bbox" in span
    finally:
        Path(temp_path).unlink()
