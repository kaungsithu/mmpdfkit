"""
Tests for converter.py and layout.py.

Conversion is tested with known Win Innwa / Zawgyi text samples
whose Unicode equivalents are verified.
"""

import unicodedata

from mmpdfkit.converter import convert_inspection, convert_span
from mmpdfkit.layout import group_lines_into_paragraphs, group_spans_into_lines


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


# ---------------------------------------------------------------------------
# converter tests
# ---------------------------------------------------------------------------


def test_win_innwa_known_conversion():
    """Known Win Innwa text → expected Unicode Myanmar."""
    result, converted = convert_span("aomfwmaqG", "win_innwa")
    assert converted is True
    assert nfc(result) == nfc("သော်တာဆွေ")  # Author name Taw Tar Swe


def test_win_innwa_title_conversion():
    result, converted = convert_span("rSefuefjcif;ESifh &J&ifhjcif;", "win_kalaw")
    assert converted is True
    assert nfc(result) == nfc("မှန်ကန်ခြင်းနှင့် ရဲရင့်ခြင်း")


def test_win_kalaw_same_as_win_innwa():
    """Win Kalaw and Win Innwa use the same encoding table."""
    text = "aomfwmaqG"
    r1, _ = convert_span(text, "win_innwa")
    r2, _ = convert_span(text, "win_kalaw")
    assert r1 == r2


def test_unicode_passthrough():
    """Unicode text should be returned unchanged."""
    text = "မှန်ကန်ခြင်း"
    result, converted = convert_span(text, "unicode")
    assert result == text
    assert converted is True


def test_unknown_encoding_returns_original():
    text = "some text"
    result, converted = convert_span(text, "unknown")
    assert result == text
    assert converted is False


def test_win_encoding_generic():
    """Generic win_encoding should convert like win_innwa."""
    result, converted = convert_span("aomfwmaqG", "win_encoding")
    assert converted is True
    assert result == "သော်တာဆွေ"


def test_convert_inspection_adds_fields():
    """convert_inspection() adds unicode_text and converted to every span."""
    fake_inspection = {
        "pages": [
            {
                "spans": [
                    {"text": "aomfwmaqG", "font_encoding": "win_innwa"},
                    {"text": "မှန်ကန်ခြင်း", "font_encoding": "unicode"},
                ]
            }
        ]
    }
    result = convert_inspection(fake_inspection)
    span0 = result["pages"][0]["spans"][0]
    span1 = result["pages"][0]["spans"][1]

    assert span0["unicode_text"] == "သော်တာဆွေ"
    assert span0["converted"] is True
    assert span1["unicode_text"] == "မှန်ကန်ခြင်း"
    assert span1["converted"] is True


def test_convert_inspection_does_not_modify_input():
    """convert_inspection() must not mutate the input dict."""
    fake = {"pages": [{"spans": [{"text": "aomfwmaqG", "font_encoding": "win_innwa"}]}]}
    original_span_keys = set(fake["pages"][0]["spans"][0].keys())
    convert_inspection(fake)
    assert set(fake["pages"][0]["spans"][0].keys()) == original_span_keys


# ---------------------------------------------------------------------------
# layout tests
# ---------------------------------------------------------------------------


def _make_span(x0, y0, x1, y1, unicode_text="word", font_size=12.0):
    return {
        "bbox": [x0, y0, x1, y1],
        "unicode_text": unicode_text,
        "font_size": font_size,
        "is_bold": False,
    }


def test_group_spans_into_lines_same_row():
    """Spans on same Y → one line."""
    spans = [
        _make_span(10, 100, 50, 115),
        _make_span(60, 101, 100, 116),  # same row, slight Y diff
    ]
    lines = group_spans_into_lines(spans)
    assert len(lines) == 1
    assert len(lines[0].spans) == 2


def test_group_spans_into_lines_two_rows():
    """Spans on different Y rows → two lines."""
    spans = [
        _make_span(10, 100, 50, 115),
        _make_span(10, 130, 50, 145),  # 15pt gap — new line
    ]
    lines = group_spans_into_lines(spans, y_tolerance=4.0)
    assert len(lines) == 2


def test_line_text_left_to_right():
    """Line.text sorts spans left to right."""
    spans = [
        _make_span(60, 100, 100, 115, unicode_text="world"),
        _make_span(10, 100, 50, 115, unicode_text="hello"),
    ]
    lines = group_spans_into_lines(spans)
    assert lines[0].text == "hello world"


def test_group_lines_into_paragraphs():
    """Large gap between lines creates a new paragraph."""
    spans = [
        _make_span(10, 100, 200, 115),  # line 1 para 1
        _make_span(10, 117, 200, 132),  # line 2 para 1 (small gap ~2)
        _make_span(10, 200, 200, 215),  # line 3 para 2 (large gap ~68)
    ]
    lines = group_spans_into_lines(spans)
    paras = group_lines_into_paragraphs(lines)
    assert len(paras) == 2


def test_heading_detected_by_font_size():
    """A line with larger font → heading paragraph."""
    spans = [
        _make_span(10, 50, 200, 75, unicode_text="Title", font_size=24.0),
        _make_span(10, 100, 200, 112, unicode_text="body", font_size=12.0),
        _make_span(10, 115, 200, 127, unicode_text="text", font_size=12.0),
    ]
    lines = group_spans_into_lines(spans, y_tolerance=4.0)
    paras = group_lines_into_paragraphs(lines)
    # First para should be a heading
    heading_paras = [p for p in paras if p.is_heading]
    assert len(heading_paras) >= 1
    assert any("Title" in p.text for p in heading_paras)
