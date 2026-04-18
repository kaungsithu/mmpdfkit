"""
Tests for font_registry and pdf_inspector.

No real PDF files required — we create minimal in-memory PDFs using fitz.
This tests our logic, not pymupdf itself.
"""

import io

import fitz
import pytest
from mmpdfkit.font_registry import classify_font, get_all_encoding_types
from mmpdfkit.pdf_inspector import _extract_from_doc

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_test_doc(text: str = "Hello", fontname: str = "helv") -> fitz.Document:
    """Create a single-page in-memory PDF with one line of text."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 100), text, fontname=fontname, fontsize=12)
    # round-trip through bytes so fitz treats it as a real PDF
    pdf_bytes = doc.tobytes()
    doc.close()
    return fitz.open(stream=io.BytesIO(pdf_bytes), filetype="pdf")


def make_empty_doc() -> fitz.Document:
    """Create a single-page PDF with no text (simulates a scanned page)."""
    doc = fitz.open()
    doc.new_page(width=595, height=842)
    pdf_bytes = doc.tobytes()
    doc.close()
    return fitz.open(stream=io.BytesIO(pdf_bytes), filetype="pdf")


# ---------------------------------------------------------------------------
# font_registry tests
# ---------------------------------------------------------------------------


def test_classify_font_zawgyi():
    assert classify_font("ZawgyiOne-Regular") == "zawgyi"
    assert classify_font("ABCDEF+ZawgyiOne") == "zawgyi"
    assert classify_font("zawgyi") == "zawgyi"


def test_classify_font_zawgyi_uppercase():
    assert classify_font("ZAWGYIONE") == "zawgyi"


def test_classify_font_unicode():
    assert classify_font("Padauk") == "unicode"
    assert classify_font("Pyidaungsu") == "unicode"
    assert classify_font("padauk") == "unicode"


def test_classify_font_unknown():
    assert classify_font("Arial") == "unknown"
    assert classify_font("") == "unknown"
    assert classify_font("Times-Roman") == "unknown"


def test_classify_font_win_innwa():
    assert classify_font("WinInnwa") == "win_innwa"
    assert classify_font("Win Innwa Bold") == "win_innwa"


def test_classify_font_case_insensitive():
    assert classify_font("ZAWGYIONE") == "zawgyi"
    assert classify_font("PADAUK") == "unicode"


def test_get_all_encoding_types_includes_unknown():
    types = get_all_encoding_types()
    assert "unknown" in types
    assert "zawgyi" in types
    assert "unicode" in types


# ---------------------------------------------------------------------------
# pdf_inspector tests
# ---------------------------------------------------------------------------


def test_scanned_heuristic_empty_doc():
    """A PDF with no text and no image blocks: blank page, not scanned."""
    doc = make_empty_doc()
    result = _extract_from_doc(doc, "test.pdf")
    # Blank page (no text, no image blocks) → page_type "blank", is_scanned False.
    assert result["is_scanned"] is False
    assert result["total_spans"] == 0
    assert result["pages"][0]["page_type"] == "blank"


def test_inspect_returns_correct_page_count():
    doc = make_test_doc("Hello")
    result = _extract_from_doc(doc, "test.pdf")
    assert result["total_pages"] == 1
    assert len(result["pages"]) == 1


def test_inspect_page_number_is_one_indexed():
    doc = make_test_doc("Hello")
    result = _extract_from_doc(doc, "test.pdf")
    assert result["pages"][0]["page_number"] == 1


def test_inspect_span_structure():
    """Spans in output must have all required fields with correct types."""
    doc = make_test_doc("Hello")
    result = _extract_from_doc(doc, "test.pdf")

    # should have at least one span
    spans = result["pages"][0]["spans"]
    assert len(spans) >= 1

    span = spans[0]
    assert isinstance(span["text"], str)
    assert isinstance(span["font_name"], str)
    assert isinstance(span["font_encoding"], str)
    assert isinstance(span["font_size"], float)
    assert isinstance(span["is_bold"], bool)
    assert isinstance(span["is_italic"], bool)
    assert isinstance(span["bbox"], list)
    assert len(span["bbox"]) == 4


def test_inspect_bbox_is_list_not_tuple():
    """bbox must be a list (JSON-serializable), not a tuple."""
    doc = make_test_doc("Test")
    result = _extract_from_doc(doc, "test.pdf")
    spans = result["pages"][0]["spans"]
    assert len(spans) >= 1
    assert isinstance(spans[0]["bbox"], list)


def test_inspect_source_file_preserved():
    doc = make_test_doc("Test")
    result = _extract_from_doc(doc, "my_source.pdf")
    assert result["source_file"] == "my_source.pdf"


def test_not_scanned_when_text_present():
    # insert_text creates one span per call, so we need 10+ calls to exceed the threshold
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    for i in range(12):
        page.insert_text(
            (72, 50 + i * 30), f"Line {i}: Myanmar PDF toolkit test", fontname="helv", fontsize=11
        )
    pdf_bytes = doc.tobytes()
    doc.close()
    doc = fitz.open(stream=io.BytesIO(pdf_bytes), filetype="pdf")

    result = _extract_from_doc(doc, "test.pdf")
    assert result["total_spans"] >= 10
    assert result["is_scanned"] is False


def test_pdf_to_markdown_scanned_with_ocr():
    """Scanned PDFs with OCR enabled produce markdown output."""
    try:
        import paddle  # noqa
    except ImportError:
        pytest.skip("paddlepaddle not available (OCR tests require full setup)")

    # Create a blank scanned-like PDF
    doc = fitz.open()
    doc.new_page(width=595, height=842)
    pdf_bytes = doc.tobytes()
    doc.close()

    import tempfile
    from pathlib import Path

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(pdf_bytes)
        temp_path = f.name

    try:
        from mmpdfkit.markdown import pdf_to_markdown

        # Should not crash, even on blank scanned PDF
        result = pdf_to_markdown(Path(temp_path), enable_ocr=True)
        assert isinstance(result, str)
        # Blank PDF → empty markdown
        assert result.strip() == ""
    finally:
        Path(temp_path).unlink()


def test_pdf_to_markdown_scanned_ocr_disabled():
    """Scanned PDFs with OCR disabled produce empty markdown."""
    doc = fitz.open()
    doc.new_page(width=595, height=842)
    pdf_bytes = doc.tobytes()
    doc.close()

    import tempfile
    from pathlib import Path

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(pdf_bytes)
        temp_path = f.name

    try:
        from mmpdfkit.markdown import pdf_to_markdown

        result = pdf_to_markdown(Path(temp_path), enable_ocr=False)
        assert isinstance(result, str)
        assert result.strip() == ""
    finally:
        Path(temp_path).unlink()


def test_cli_no_ocr_flag():
    """--no-ocr and --include-images flags are accepted by the markdown CLI."""
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "mmpdfkit.markdown", "--help"],
        capture_output=True,
        text=True,
    )
    assert "--no-ocr" in result.stdout
    assert "--include-images" in result.stdout
