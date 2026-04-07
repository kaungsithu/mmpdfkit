"""
converter.py — Convert pre-Unicode Myanmar text spans to Unicode.

Win Myanmar fonts (Win Innwa, Win Kalaw, Win Dagon, etc.) store characters as
ASCII bytes in PDFs. The python-myanmar library's 'wininnwa' encoding covers
all Win Myanmar fonts since they share the same character mapping table.

Zawgyi uses Myanmar Unicode codepoints (U+1000-U+109F) in visual order;
python-myanmar handles that too.

Conversion is non-destructive: the original 'text' field is kept, and
'unicode_text' + 'converted' fields are added to each span.
"""

from __future__ import annotations

from myanmar.converter import convert as mm_convert
from myanmartools import ZawgyiDetector

# Singleton detector — loading it is expensive
_detector = ZawgyiDetector()

# Mapping from our encoding types to python-myanmar encoding names
_ENCODING_MAP: dict[str, str] = {
    "win_innwa": "wininnwa",
    "win_kalaw": "wininnwa",  # Win Kalaw uses the same table as Win Innwa
    "winburmese": "wininnwa",  # Win Burmese / Wina — same family
    "win_encoding": "wininnwa",  # Generic Win* catch-all
    "myanmar3": "wininnwa",  # Pre-2008 Myanmar3 uses Win-style encoding
    "masterpiece": "wininnwa",  # Masterpiece uses similar ASCII encoding
    "zawgyi": "zawgyi",
    "unicode": "unicode",
}


def convert_span(text: str, encoding_type: str) -> tuple[str, bool]:
    """
    Convert a single text span to Unicode Myanmar.

    Args:
        text: Raw text as extracted from the PDF.
        encoding_type: Encoding type string from font_registry.classify_font().

    Returns:
        (unicode_text, was_converted) tuple.
        was_converted is False only for 'unknown' encoding types.
    """
    mm_encoding = _ENCODING_MAP.get(encoding_type)

    if mm_encoding == "unicode":
        return text, True  # already Unicode, pass through

    if mm_encoding is None:
        # Unknown encoding — return as-is, flag as unconverted
        return text, False

    try:
        result = mm_convert(text, mm_encoding, "unicode")
        return result, True
    except Exception:
        # Conversion failed (e.g. unexpected characters) — return original
        return text, False


def detect_and_convert(text: str) -> tuple[str, str]:
    """
    Auto-detect whether text is Zawgyi or Unicode and convert if needed.

    Uses ZawgyiDetector to determine encoding. Only useful when the font
    name is not available or font_encoding is 'unknown'.

    Returns:
        (unicode_text, detected_encoding) where detected_encoding is
        'zawgyi', 'unicode', or 'unknown'.
    """
    try:
        prob = _detector.get_zawgyi_probability(text)
    except Exception:
        return text, "unknown"

    if prob > 0.9:
        try:
            return mm_convert(text, "zawgyi", "unicode"), "zawgyi"
        except Exception:
            return text, "zawgyi"
    elif prob < 0.1:
        return text, "unicode"
    else:
        # Ambiguous — return as-is
        return text, "unknown"


def convert_inspection(inspection: dict) -> dict:
    """
    Add 'unicode_text' and 'converted' fields to every span in an inspection dict.

    Takes the output of pdf_inspector.inspect_pdf() and returns a new dict
    with the same structure, where each span gains:
      "unicode_text": str   — converted Unicode text (or original if unknown)
      "converted": bool     — True if a conversion was performed

    The input dict is not modified.

    Args:
        inspection: Dict from pdf_inspector.inspect_pdf().

    Returns:
        New dict with unicode_text added to every span.
    """
    import copy

    result = copy.deepcopy(inspection)
    for page in result["pages"]:
        for span in page["spans"]:
            unicode_text, converted = convert_span(span["text"], span["font_encoding"])
            span["unicode_text"] = unicode_text
            span["converted"] = converted
    return result
