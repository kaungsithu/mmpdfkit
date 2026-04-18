"""Tests for OCR module."""
import tempfile
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

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(pdf_bytes)
        temp_path = Path(f.name)

    try:
        with pytest.raises(ValueError, match="OCR disabled"):
            extract_and_ocr(temp_path, enable_ocr=False)
    finally:
        temp_path.unlink()


def test_extract_and_ocr_missing_onnxruntime(monkeypatch):
    """extract_and_ocr raises ImportError if onnxruntime is not installed."""
    import builtins

    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "numpy":
            raise ImportError("No module named 'numpy'")
        return real_import(name, *args, **kwargs)

    pdf_bytes = make_blank_pdf_bytes()

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(pdf_bytes)
        temp_path = Path(f.name)

    try:
        monkeypatch.setattr(builtins, "__import__", mock_import)
        with pytest.raises(ImportError, match="pip install mmpdfkit"):
            extract_and_ocr(temp_path, enable_ocr=True)
    finally:
        temp_path.unlink()


def test_extract_and_ocr_returns_spans():
    """extract_and_ocr returns list of span dicts (requires onnxruntime installed)."""
    pytest.importorskip("onnxruntime")

    pdf_bytes = make_blank_pdf_bytes()

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(pdf_bytes)
        temp_path = Path(f.name)

    try:
        result = extract_and_ocr(temp_path, enable_ocr=True)

        # Should return a list of per-page span lists
        assert isinstance(result, list)
        assert len(result) == 1  # one page in blank PDF

        # Each item is a list of spans for that page
        page_spans = result[0]
        assert isinstance(page_spans, list)

        # Each span should be a valid span dict
        for span in page_spans:
            assert isinstance(span, dict)
            assert "text" in span
            assert "font_name" in span
            assert "font_encoding" in span
            assert "font_size" in span
            assert "is_bold" in span
            assert "is_italic" in span
            assert "bbox" in span
            assert len(span["bbox"]) == 4
    finally:
        temp_path.unlink()
