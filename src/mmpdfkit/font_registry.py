"""
font_registry.py — Myanmar font name to encoding type lookup.

PDF exporters mangle font names in several ways:
  - Subset prefixes: "ABCDEF+ZawgyiOne" (6 random uppercase letters + plus sign)
  - Style suffixes: "-Bold", "-Italic", "Regular", ",Bold"
  - Case changes: "zawgyione", "ZAWGYIONE"

We handle all of these with case-insensitive substring matching.
New font names can be added by appending to _FONT_PATTERNS.

Encoding types:
  zawgyi       - Zawgyi-One and compatible (pre-Unicode, dominant 2006-2019)
  win_innwa    — Win Innwa family (pre-Unicode, Win Myanmar Systems)
  win_kalaw    — Win Kalaw (pre-Unicode, Win Myanmar Systems)
  winburmese   — Wina / WinBurmese (pre-Unicode)
  win_encoding — Generic Win* family catch-all (80+ fonts, same ASCII-range encoding)
  myanmar3     — Myanmar3 font (ambiguous: pre-Unicode before 2008, Unicode after)
  masterpiece  — Masterpiece (pre-Unicode)
  unicode      — Known Unicode-compliant fonts (Padauk, Pyidaungsu, Noto, etc.)
  unknown      — Not matched; inspect manually and add to registry
"""

# Each entry: (substring_to_match_case_insensitively, encoding_type_string)
# Order matters — first match wins. Specific patterns must come before generic ones.
_FONT_PATTERNS: list[tuple[str, str]] = [
    # --- Zawgyi family (pre-Unicode, most common Myanmar encoding 2006-2019) ---
    ("zawgyi", "zawgyi"),
    ("zg", "zawgyi"),  # shorthand seen in some PDFs
    ("myazedi", "zawgyi"),  # MyaZedi uses Zawgyi-compatible encoding
    # --- Win Unicode variants — MUST come before generic "win" catch-all ---
    ("winuni", "unicode"),  # WinUniInnwa (Win Innwa version 5.x, Unicode)
    ("masterpiece uni", "unicode"),  # Masterpiece Uni Round/Sans
    ("masterpieceuniround", "unicode"),
    ("masterpieceunisans", "unicode"),
    # --- Win Innwa (pre-Unicode, specific subtype kept for conversion purposes) ---
    ("wininnwa", "win_innwa"),
    ("win innwa", "win_innwa"),
    ("win_innwa", "win_innwa"),
    # --- Win Kalaw (pre-Unicode) ---
    ("winkalaw", "win_kalaw"),
    ("win kalaw", "win_kalaw"),
    # --- Wina / WinBurmese (pre-Unicode) ---
    ("winburmese", "winburmese"),
    ("wina", "winburmese"),
    # --- Generic Win* catch-all (covers 80+ Win Myanmar fonts) ---
    # Catches: WinDagon, WinMandalay, WinSittway, WinAmarapura, WinPonnya,
    #          WinHlaing, WinInnLay, WinKyemone, WinLashio, WinLoikaw,
    #          WinMawlamyine, WinMonotype, WinPyu, WinTaungGyi, WinThanLyin,
    #          WinYadanapon, WinTypewriter, etc.
    # All use the same ASCII-range pre-Unicode encoding.
    # Must come AFTER all specific win_* entries above.
    ("win", "win_encoding"),
    # --- Myanmar3 (ambiguous — pre-Unicode before ~2008, Unicode after) ---
    # Cannot distinguish version by font name alone; flagged as own type.
    # If you know the document era, treat myanmar3 as pre-Unicode for pre-2010 docs.
    ("myanmar3", "myanmar3"),
    ("mm3", "myanmar3"),
    # --- Masterpiece (pre-Unicode, non-Uni variants only — Uni caught above) ---
    ("masterpiece", "masterpiece"),
    # --- Unicode fonts (known compliant implementations) ---
    # SIL / Open Source
    ("padauk", "unicode"),  # Padauk — first true Burmese Unicode font (SIL)
    ("pyidaungsu", "unicode"),  # Pyidaungsu — Myanmar govt standard (2014+)
    ("gantgaw", "unicode"),  # Gantgaw — display font, SIL OFL
    ("tharlon", "unicode"),
    ("yunghkio", "unicode"),
    ("ywini", "unicode"),
    ("uniburma", "unicode"),
    ("thanlwin", "unicode"),  # ThanLwinSoft
    ("ayar", "unicode"),
    # Google
    ("noto sans myanmar", "unicode"),
    ("noto serif myanmar", "unicode"),
    ("notosansmyanmar", "unicode"),
    ("notoserifmyanmar", "unicode"),
    # Microsoft (Windows built-in)
    ("myanmar text", "unicode"),
    ("myanmartext", "unicode"),
    ("mmrtext", "unicode"),  # file-level name of Myanmar Text font
    # Apple (macOS/iOS built-in)
    ("myanmar sangam", "unicode"),
    ("myanmarsangam", "unicode"),
    # Other Unicode
    ("jasmine unicode", "unicode"),
    ("jasmineunicode", "unicode"),
]


def classify_font(font_name: str) -> str:
    """
    Return the encoding type for a given PDF font name.

    Matching is case-insensitive substring search through _FONT_PATTERNS.
    First match wins. Returns 'unknown' if no pattern matches.

    Font names from PDFs often look like:
      "ABCDEF+ZawgyiOne-Regular"   → subset prefix added by PDF tools
      "ZawgyiOne,Bold"
      "WinKalaw"
    We lowercase and search for substrings, so all of those match correctly.

    Args:
        font_name: Raw font name string as reported by pymupdf.

    Returns:
        One of: 'zawgyi', 'win_innwa', 'win_kalaw', 'winburmese',
                'win_encoding', 'myanmar3', 'masterpiece', 'unicode', 'unknown'
    """
    normalized = font_name.lower().strip()
    for pattern, encoding_type in _FONT_PATTERNS:
        if pattern in normalized:
            return encoding_type
    return "unknown"


def get_all_encoding_types() -> list[str]:
    """Return deduplicated list of all encoding types in the registry, plus 'unknown'."""
    seen: list[str] = []
    for _, enc in _FONT_PATTERNS:
        if enc not in seen:
            seen.append(enc)
    seen.append("unknown")
    return seen
