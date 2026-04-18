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


def _looks_like_win_myanmar(text: str) -> bool:
    """Return True if text is likely WinMyanmar/WinInnwa encoded.

    Win Myanmar fonts map Myanmar glyphs to Latin-1 Supplement codepoints
    (U+0080–U+00FF). If the majority of non-whitespace characters fall in
    that range (and none are actual Myanmar Unicode), it's WinMyanmar.
    """
    chars = [c for c in text if not c.isspace()]
    if len(chars) < 3:
        return False
    has_myanmar_unicode = any(0x1000 <= ord(c) <= 0x109F for c in chars)
    if has_myanmar_unicode:
        return False
    win_range = sum(1 for c in chars if 0x80 <= ord(c) <= 0xFF)
    return win_range / len(chars) > 0.7


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
        # Unknown font name — fall back to content-based detection.
        # WinMyanmar fonts are sometimes embedded with obfuscated names (e.g.
        # "ZTR489.tmp,Bold") that don't match any registry pattern.
        if _looks_like_win_myanmar(text):
            try:
                return mm_convert(text, "wininnwa", "unicode"), True
            except Exception:
                pass
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
