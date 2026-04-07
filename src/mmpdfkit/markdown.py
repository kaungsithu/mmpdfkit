"""
markdown.py — Generate Markdown output from reconstructed page layout.

Takes Paragraph objects from layout.py and produces clean, LLM-ready Markdown.
Pages are separated by a horizontal rule so the document structure is preserved.

CLI usage:
    python -m mmpdfkit.markdown samples/example.pdf
    python -m mmpdfkit.markdown samples/          # all PDFs in directory
"""

from __future__ import annotations

from pathlib import Path

from mmpdfkit.layout import Paragraph, reconstruct_page


def paragraph_to_markdown(para: Paragraph) -> str:
    """Convert one Paragraph to a Markdown string. Returns '' for empty paragraphs."""
    text = para.text.strip()
    if not text:
        return ""
    if para.is_heading:
        prefix = "#" * para.heading_level
        # headings must be single-line — join wrapped lines with a space
        text = " ".join(text.splitlines())
        return f"{prefix} {text}"
    return text


def page_to_markdown(paragraphs: list[Paragraph]) -> str:
    """Convert one page's paragraphs to Markdown, double-newline separated."""
    parts = [paragraph_to_markdown(p) for p in paragraphs]
    parts = [p for p in parts if p]
    return "\n\n".join(parts)


def document_to_markdown(pages_paragraphs: list[list[Paragraph]]) -> str:
    """
    Combine all pages into a single Markdown document.
    Non-empty pages are separated by '---' (horizontal rule).
    """
    page_texts = [page_to_markdown(pp) for pp in pages_paragraphs]
    page_texts = [t for t in page_texts if t.strip()]
    return "\n\n---\n\n".join(page_texts)


def pdf_to_markdown(
    pdf_path_or_inspection: Path | dict, converted: dict | None = None, enable_ocr: bool = True
) -> str:
    """
    Full pipeline: PDF → Markdown.

    For scanned PDFs (is_scanned: true):
    - Runs OCR to extract text (unless enable_ocr=False)
    - Converts to Unicode via detect_and_convert

    For digital PDFs: proceeds normally

    Args:
        pdf_path_or_inspection: Path to PDF or inspection dict
        converted: Pre-converted inspection dict (optional, for reuse)
        enable_ocr: Whether to run OCR on scanned documents (default True)

    Returns:
        Markdown string of the entire document
    """
    from pathlib import Path

    from mmpdfkit.converter import convert_inspection
    from mmpdfkit.pdf_inspector import inspect_pdf

    # Handle both Path and pre-computed inspection dict
    if isinstance(pdf_path_or_inspection, dict):
        inspection = pdf_path_or_inspection
        converted = converted or convert_inspection(inspection)
    else:
        pdf_path = Path(pdf_path_or_inspection)
        inspection = inspect_pdf(pdf_path)

        # Check config for OCR preference (CLI flag overrides)
        from mmpdfkit.config import load_config

        config = load_config()
        # enable_ocr param takes precedence, then config
        should_ocr = enable_ocr and config.get("enable_ocr", True)

        # For scanned PDFs, try OCR if enabled
        if inspection["is_scanned"] and should_ocr:
            try:
                from mmpdfkit.ocr import extract_and_ocr

                ocr_spans = extract_and_ocr(pdf_path, enable_ocr=True)
                # Add OCR spans to inspection
                for page_idx, page in enumerate(inspection["pages"]):
                    if page_idx < len(inspection["pages"]):
                        page["spans"].extend(ocr_spans)
            except (ImportError, ValueError):
                # OCR not available or disabled — proceed without it
                pass

        converted = convert_inspection(inspection)

    pages_paragraphs = [reconstruct_page(page) for page in converted["pages"]]
    return document_to_markdown(pages_paragraphs)


def save_markdown(markdown: str, output_path: Path) -> None:
    """Write markdown string to file (UTF-8). Prints confirmation."""
    output_path.write_text(markdown, encoding="utf-8")
    print(f"Saved → {output_path}  ({len(markdown):,} chars)")


def main() -> None:
    """Entry point: python -m mmpdfkit.markdown <path> [--output-dir DIR]"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Convert Myanmar PDF to Markdown via Unicode conversion."
    )
    parser.add_argument("path", help="PDF file or directory of PDFs.")
    parser.add_argument(
        "--output-dir", default="output", help="Directory for .md output files (default: ./output)"
    )
    parser.add_argument(
        "--no-ocr",
        action="store_true",
        help="Disable OCR for scanned PDFs (use config or this flag)",
    )
    args = parser.parse_args()

    input_path = Path(args.path)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    pdfs = sorted(input_path.glob("*.pdf")) if input_path.is_dir() else [input_path]
    if not pdfs:
        print(f"No PDF files found in {input_path}")
        return

    for pdf in pdfs:
        print(f"Converting {pdf.name} ...")
        md = pdf_to_markdown(pdf, enable_ocr=not args.no_ocr)
        out = output_dir / (pdf.stem + ".md")
        save_markdown(md, out)


if __name__ == "__main__":
    main()
