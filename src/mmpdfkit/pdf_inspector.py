"""
pdf_inspector.py — Extract text spans and font metadata from Myanmar PDFs.

This module inspects PDFs without converting anything. The goal is to understand
what fonts are used and how text is encoded before attempting any transformation.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import fitz  # pymupdf

from mmpdfkit.font_registry import classify_font


@dataclass
class SpanInfo:
    text: str
    font_name: str
    font_encoding: str
    font_size: float
    is_bold: bool
    is_italic: bool
    bbox: list[float]  # [x0, y0, x1, y1]


@dataclass
class PageInfo:
    page_number: int  # 1-indexed
    width: float
    height: float
    spans: list[SpanInfo] = field(default_factory=list)


def _extract_from_doc(doc: fitz.Document, source_name: str) -> dict:
    """
    Extract all text spans from an already-opened fitz.Document.

    Separated from inspect_pdf() so tests can pass an in-memory document
    without needing a file on disk.

    Args:
        doc: An open fitz.Document.
        source_name: String to use as "source_file" in the output dict.

    Returns:
        Dict matching the JSON output schema.
    """
    pages: list[dict] = []
    fonts_found: dict[str, str] = {}  # raw font name → encoding type
    spans_by_encoding: dict[str, int] = {}
    total_spans = 0

    for page_index in range(doc.page_count):
        page = doc[page_index]
        page_spans: list[dict] = []

        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            # type 1 = image block, skip it
            if block["type"] != 0:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"]
                    # skip whitespace-only spans — pymupdf emits these for spacing gaps
                    if not text.strip():
                        continue

                    font_name = span["font"]
                    font_size = span["size"]
                    flags = span["flags"]
                    is_bold = bool(flags & 16)
                    is_italic = bool(flags & 2)
                    bbox = list(span["bbox"])  # convert tuple to list for JSON

                    encoding = classify_font(font_name)

                    # track unique fonts seen in this document
                    if font_name not in fonts_found:
                        fonts_found[font_name] = encoding

                    # accumulate span counts per encoding type
                    spans_by_encoding[encoding] = spans_by_encoding.get(encoding, 0) + 1
                    total_spans += 1

                    page_spans.append(
                        asdict(
                            SpanInfo(
                                text=text,
                                font_name=font_name,
                                font_encoding=encoding,
                                font_size=font_size,
                                is_bold=is_bold,
                                is_italic=is_italic,
                                bbox=bbox,
                            )
                        )
                    )

        pages.append(
            asdict(
                PageInfo(
                    page_number=page_index + 1,
                    width=page.rect.width,
                    height=page.rect.height,
                    spans=[],  # will be replaced below
                )
            )
        )
        pages[-1]["spans"] = page_spans

    return {
        "source_file": source_name,
        "total_pages": doc.page_count,
        "is_scanned": total_spans < 10,
        "total_spans": total_spans,
        "fonts_found": fonts_found,
        "spans_by_encoding": spans_by_encoding,
        "pages": pages,
    }


def inspect_pdf(pdf_path: Path) -> dict:
    """
    Open a PDF file and extract all text spans with font metadata.

    Returns a dict matching the JSON output schema. Does not write any files.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Dict ready for json.dumps().

    Raises:
        FileNotFoundError: if pdf_path does not exist.
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    doc = fitz.open(str(pdf_path))
    try:
        return _extract_from_doc(doc, str(pdf_path))
    finally:
        doc.close()


def inspect_and_save(pdf_path: Path, output_dir: Path) -> Path:
    """
    Inspect a PDF and write the JSON report to output_dir.

    Output filename: output_dir / (pdf_path.stem + "_inspection.json")

    Prints a one-line summary to stdout after saving.

    Args:
        pdf_path: Path to the PDF file.
        output_dir: Directory to write JSON into (must already exist).

    Returns:
        Path to the written JSON file.
    """
    result = inspect_pdf(pdf_path)

    out_path = output_dir / (pdf_path.stem + "_inspection.json")
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    # build summary line for stdout
    enc_summary = " ".join(f"{k}={v}" for k, v in result["spans_by_encoding"].items())
    print(
        f"Inspected {pdf_path.name} → {out_path} "
        f"({result['total_pages']} pages, {result['total_spans']} spans"
        + (f", fonts: {enc_summary}" if enc_summary else "")
        + ")"
    )

    return out_path


def main() -> None:
    """Entry point for: python -m mmpdfkit.pdf_inspector <path>"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Inspect Myanmar PDF files and extract font/text metadata."
    )
    parser.add_argument("path", help="Path to a PDF file or directory containing PDFs.")
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory for JSON output (default: ./output)",
    )
    args = parser.parse_args()

    input_path = Path(args.path)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if input_path.is_dir():
        pdf_files = sorted(input_path.glob("*.pdf"))
        if not pdf_files:
            print(f"No PDF files found in {input_path}")
            return
        for pdf in pdf_files:
            inspect_and_save(pdf, output_dir)
    elif input_path.is_file():
        inspect_and_save(input_path, output_dir)
    else:
        print(f"Error: {input_path} is not a file or directory.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
