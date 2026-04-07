"""Command-line interface for mmpdfkit."""

import argparse
import sys
from pathlib import Path

from mmpdfkit.markdown import pdf_to_markdown, save_markdown
from mmpdfkit.pdf_inspector import inspect_and_save


def main() -> None:
    """Main CLI entry point with subcommands for convert and inspect."""
    parser = argparse.ArgumentParser(
        prog="mmpdfkit",
        description="Myanmar PDF inspection, Unicode conversion, and OCR toolkit",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Convert command (default if no subcommand)
    convert_parser = subparsers.add_parser(
        "convert",
        help="Convert PDF to Markdown (default)",
        add_help=False,
    )
    _add_convert_args(convert_parser)

    # Inspect command
    inspect_parser = subparsers.add_parser(
        "inspect",
        help="Extract PDF metadata as JSON",
    )
    _add_inspect_args(inspect_parser)

    # Handle positional path argument (convert is default if no subcommand)
    # This allows: mmpdfkit file.pdf (without explicit "convert")
    args = parser.parse_args()

    # If no subcommand, treat first arg as path for convert
    if args.command is None:
        if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
            # Re-parse with convert parser to capture convert-specific args
            args = convert_parser.parse_args(sys.argv[1:])
            args.command = "convert"
        else:
            parser.print_help()
            sys.exit(1)

    # Route to appropriate command
    if args.command == "convert":
        convert_pdfs(args)
    elif args.command == "inspect":
        inspect_pdfs(args)
    else:
        parser.print_help()
        sys.exit(1)


def _add_convert_args(parser: argparse.ArgumentParser) -> None:
    """Add arguments for convert subcommand."""
    parser.add_argument(
        "path",
        help="PDF file or directory of PDFs",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory (default: same as input PDF)",
    )
    parser.add_argument(
        "--no-ocr",
        action="store_true",
        help="Disable OCR for scanned documents",
    )


def _add_inspect_args(parser: argparse.ArgumentParser) -> None:
    """Add arguments for inspect subcommand."""
    parser.add_argument(
        "path",
        help="PDF file or directory of PDFs",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory (default: same as input PDF)",
    )


def _collect_pdfs(input_path: Path) -> list[Path]:
    """Collect PDFs from a file or directory.

    Args:
        input_path: Path to a PDF file or directory containing PDFs

    Returns:
        Sorted list of PDF Path objects. Empty list if none found.
    """
    if input_path.is_dir():
        return sorted(input_path.glob("*.pdf"))
    else:
        return [input_path] if input_path.suffix.lower() == ".pdf" else []


def _resolve_output_dir(output_dir_arg: str | None) -> Path | None:
    """Resolve output directory from CLI argument.

    Args:
        output_dir_arg: User-provided output directory path or None

    Returns:
        Path object if specified, None for default (same as input)
    """
    return Path(output_dir_arg) if output_dir_arg else None


def convert_pdfs(args: argparse.Namespace) -> None:
    """Convert PDF(s) to Markdown."""
    input_path = Path(args.path)
    pdfs = _collect_pdfs(input_path)

    if not pdfs:
        print(f"No PDF files found in {input_path}")
        return

    # Resolve output directory once
    output_dir = _resolve_output_dir(args.output_dir)
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    for pdf in pdfs:
        print(f"Converting {pdf.name} ...")

        try:
            # Generate markdown
            md = pdf_to_markdown(pdf, enable_ocr=not args.no_ocr)

            # Determine output path
            out = output_dir / (pdf.stem + ".md") if output_dir else pdf.parent / (pdf.stem + ".md")

            save_markdown(md, out)
        except Exception as e:
            print(f"Error converting {pdf.name}: {e}", file=sys.stderr)


def inspect_pdfs(args: argparse.Namespace) -> None:
    """Inspect PDF(s) and extract metadata as JSON."""
    input_path = Path(args.path)
    pdfs = _collect_pdfs(input_path)

    if not pdfs:
        print(f"No PDF files found in {input_path}")
        return

    # Resolve output directory
    output_dir = _resolve_output_dir(args.output_dir)

    for pdf in pdfs:
        print(f"Inspecting {pdf.name} ...")

        try:
            # Use provided output dir or default to PDF's parent directory
            out_dir = output_dir if output_dir else pdf.parent
            inspect_and_save(pdf, out_dir)
        except Exception as e:
            print(f"Error inspecting {pdf.name}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
