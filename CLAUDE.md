# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**mmpdfkit** is a Myanmar PDF inspection and Unicode conversion toolkit. It extracts text spans and font metadata from Myanmar PDFs (Step 1 of the roadmap), detects font encoding types (Win Myanmar, Zawgyi, Unicode), and converts pre-Unicode text to proper Unicode Myanmar.

### Architecture

The project has a pipeline structure with distinct phases planned in the roadmap:

1. **PDF Inspection** (current) — Extract text spans and font metadata from PDFs without modification
2. **Encoding Detection & Conversion** — Convert Win Myanmar, Zawgyi, and other legacy encodings to Unicode
3. **Layout Reconstruction** — Preserve document structure and spacing
4. **Markdown Generation** — Output converted text as Markdown

Core modules:

- **`pdf_inspector.py`** — Reads PDFs using PyMuPDF (`fitz`), extracts text spans with font names, sizes, bounding boxes, and style flags (bold/italic). Key functions: `inspect_pdf()`, `inspect_and_save()`. Produces JSON inspection reports with font metadata for each span.

- **`converter.py`** — Converts text spans to Unicode Myanmar using `python-myanmar` library. Maps font names (Win Innwa, Win Kalaw, Zawgyi, etc.) to encoding types, then uses appropriate conversion strategy. Key functions: `convert_span()`, `detect_and_convert()`, `convert_inspection()`. Also detects Zawgyi vs Unicode using `ZawgyiDetector`.

- **`font_registry.py`** — Classifies fonts into encoding types (win_innwa, zawgyi, unicode, unknown) using regex patterns. Single responsibility: convert raw font name → encoding type.

- **`layout.py`** — Layout reconstruction logic (stub for future roadmap phases).

- **`markdown.py`** — Markdown generation (stub for future roadmap phases).

Output format is JSON: each PDF produces a document structure with pages, spans, and per-span metadata (font, encoding, position, conversion status).

## Build & Install

```bash
# Install in development mode (editable install with dev dependencies)
pip install -e ".[dev]"

# Build distribution packages
python -m build
```

## Running Commands

```bash
# Inspect a single PDF and save JSON report to output/
python -m mmpdfkit.pdf_inspector samples/example.pdf

# Inspect all PDFs in a directory
python -m mmpdfkit.pdf_inspector samples/

# Custom output directory
python -m mmpdfkit.pdf_inspector samples/ --output-dir my_output/
```

## Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_pdf_inspector.py

# Run specific test function
pytest tests/test_pdf_inspector.py::test_function_name

# Run with verbose output
pytest -v

# Run with output capture disabled (see print statements)
pytest -s
```

Test files:
- `tests/test_pdf_inspector.py` — Tests for PDF extraction and span parsing
- `tests/test_converter.py` — Tests for encoding detection and conversion

## Key Dependencies

- **`pymupdf` (fitz)** — PDF reading and text extraction with bounding boxes and font metadata
- **`python-myanmar`** — Font encoding conversion (Win Myanmar, Zawgyi → Unicode)
- **`myanmartools`** — ZawgyiDetector for detecting Zawgyi vs Unicode text

## Important Notes for Development

### Text Extraction & Font Metadata

- PyMuPDF's `page.get_text("dict")` returns nested structures: documents → pages → blocks → lines → spans
- Image blocks (type 1) are skipped; only text blocks (type 0) are processed
- Whitespace-only spans from PyMuPDF are filtered out during extraction
- Font names are raw strings like "BCDFAA+ShanNewMyamar-Book"; these must be classified before knowing the encoding

### Encoding Strategy

- Win Myanmar fonts (Win Innwa, Win Kalaw, etc.) all map to the same conversion table ("wininnwa")
- Zawgyi uses Myanmar Unicode codepoints (U+1000-U+109F) in visual order — requires different conversion path
- Unicode Myanmar is already correct — just pass through
- Conversion is non-destructive: original `text` field is preserved; `unicode_text` and `converted` fields are added

### JSON Output Schema

Inspection results follow this structure:

```json
{
  "source_file": "path/to/file.pdf",
  "total_pages": 5,
  "is_scanned": false,
  "total_spans": 1024,
  "fonts_found": {
    "BCDFAA+ShanNewMyamar-Book": "win_innwa",
    "Zawgyi-One": "zawgyi"
  },
  "spans_by_encoding": {
    "win_innwa": 800,
    "zawgyi": 100,
    "unicode": 124
  },
  "pages": [
    {
      "page_number": 1,
      "width": 612.0,
      "height": 792.0,
      "spans": [
        {
          "text": "...",
          "font_name": "BCDFAA+ShanNewMyamar-Book",
          "font_encoding": "win_innwa",
          "font_size": 12.0,
          "is_bold": false,
          "is_italic": false,
          "bbox": [72, 72, 200, 84]
        }
      ]
    }
  ]
}
```

### Roadmap Context

The project is structured to complete features sequentially. PDF inspection (Step 1) must be stable before moving to Zawgyi → Unicode conversion (Step 2), which in turn is needed for layout reconstruction (Step 3) and final Markdown output (Step 4). Each step builds on the previous one.
