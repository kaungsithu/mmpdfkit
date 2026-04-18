"""
markdown.py — Generate Markdown output from reconstructed page layout.

Takes Paragraph objects from layout.py and produces clean, LLM-ready Markdown.
Pages are separated by a horizontal rule so the document structure is preserved.

CLI usage:
    python -m mmpdfkit.markdown samples/example.pdf
    python -m mmpdfkit.markdown samples/          # all PDFs in directory
"""

from __future__ import annotations

import sys
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


def _render_page_png(pdf_path: Path, page_index: int, output_path: Path) -> None:
    """Render a PDF page to a PNG file at 150 DPI (1× scale)."""
    import fitz

    doc = fitz.open(str(pdf_path))
    try:
        page = doc[page_index]
        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
        output_path.write_bytes(pix.tobytes("png"))
    finally:
        doc.close()


def pdf_to_markdown(
    pdf_path_or_inspection: Path | dict,
    converted: dict | None = None,
    enable_ocr: bool = True,
    output_dir: Path | None = None,
    include_images: bool = False,
) -> str:
    """
    Full pipeline: PDF → Markdown.

    For scanned PDFs (is_scanned: true) or pages with page_type "image":
    - Runs OCR to extract text (unless enable_ocr=False)
    - If include_images=True, also saves a PNG and embeds an image tag

    For digital PDFs: proceeds normally.

    Args:
        pdf_path_or_inspection: Path to PDF or inspection dict
        converted: Pre-converted inspection dict (optional, for reuse)
        enable_ocr: Whether to run OCR on image pages (default True)
        output_dir: Directory for image files (required when include_images=True)
        include_images: Embed PNG screenshots for image-only pages

    Returns:
        Markdown string of the entire document
    """
    from mmpdfkit.converter import convert_inspection
    from mmpdfkit.pdf_inspector import inspect_pdf

    # Resolve PDF path and inspection dict
    if isinstance(pdf_path_or_inspection, dict):
        inspection = pdf_path_or_inspection
        pdf_path = None
        converted = converted or convert_inspection(inspection)
    else:
        pdf_path = Path(pdf_path_or_inspection)
        inspection = inspect_pdf(pdf_path)

        from mmpdfkit.config import load_config

        config = load_config()
        should_ocr = enable_ocr and config.get("enable_ocr", True)

        if should_ocr:
            _run_ocr_for_image_pages(inspection, pdf_path)

        converted = convert_inspection(inspection)

    # Build per-page Markdown, handling image pages specially
    page_parts: list[str] = []
    for page_idx, page in enumerate(converted["pages"]):
        page_num = page["page_number"]
        page_type = page.get("page_type", "typed")

        if page_type == "blank":
            continue

        if page_type == "image" and not page["spans"]:
            # Image page with no OCR text — either embed PNG or emit placeholder
            if include_images and output_dir is not None and pdf_path is not None:
                images_dir = output_dir / "images"
                images_dir.mkdir(parents=True, exist_ok=True)
                img_filename = f"page_{page_num:03d}.png"
                _render_page_png(pdf_path, page_idx, images_dir / img_filename)
                page_parts.append(f"![Page {page_num}](images/{img_filename})")
            else:
                # No OCR result and images not requested — skip silently
                pass
            continue

        paragraphs = reconstruct_page(page)
        text = page_to_markdown(paragraphs)
        if text.strip():
            page_parts.append(text)

    return "\n\n---\n\n".join(page_parts)


def _run_ocr_for_image_pages(inspection: dict, pdf_path: Path) -> None:
    """
    Run CRNN OCR on every page classified as "image" and inject spans in-place.

    Modifies inspection["pages"] directly. Silently skips if OCR deps are missing.
    """
    import fitz

    image_pages = [
        (idx, p) for idx, p in enumerate(inspection["pages"])
        if p.get("page_type") == "image"
    ]
    if not image_pages:
        # Also check the old is_scanned path (typed PDFs with low span count)
        if not inspection.get("is_scanned"):
            return
        image_pages = [(idx, p) for idx, p in enumerate(inspection["pages"])]

    try:
        import numpy as np

        from mmpdfkit.ocr import ocr_page_spans
    except ImportError as e:
        print(f"Warning: {e}", file=sys.stderr)
        print(
            "  This PDF contains scanned pages. Run: pip install mmpdfkit[ocr]",
            file=sys.stderr,
        )
        return

    doc = fitz.open(str(pdf_path))
    try:
        for page_idx, page in image_pages:
            fitz_page = doc[page_idx]
            pix = fitz_page.get_pixmap(matrix=fitz.Matrix(2, 2), colorspace=fitz.csGRAY)
            page_gray = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width
            )
            spans = ocr_page_spans(page_gray, fitz_page.rect.width, fitz_page.rect.height)
            page["spans"].extend(spans)
            if spans:
                # Upgrade page_type so reconstruct_page treats it as text
                page["page_type"] = "scanned_text"
    finally:
        doc.close()


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
    parser.add_argument(
        "--include-images",
        action="store_true",
        help="Save image-only pages as PNG and embed in Markdown",
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
        # Per-PDF sub-directory: output_dir/{stem}/{stem}.md
        pdf_out_dir = output_dir / pdf.stem
        pdf_out_dir.mkdir(parents=True, exist_ok=True)
        md = pdf_to_markdown(
            pdf,
            enable_ocr=not args.no_ocr,
            output_dir=pdf_out_dir,
            include_images=args.include_images,
        )
        out = pdf_out_dir / (pdf.stem + ".md")
        save_markdown(md, out)


if __name__ == "__main__":
    main()
