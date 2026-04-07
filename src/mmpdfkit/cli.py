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
            args = parser.parse_args([])
            args.command = "convert"
            args.path = Path(sys.argv[1])
            if len(sys.argv) > 2:
                # Re-parse to capture optional args
                args = convert_parser.parse_args(sys.argv[1:])
        else:
            parser.print_help()
            sys.exit(1)

    # Route to appropriate command
    if args.command == "convert" or args.command is None:
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


def convert_pdfs(args: argparse.Namespace) -> None:
    """Convert PDF(s) to Markdown."""
    input_path = Path(args.path)

    # Collect PDFs
    if input_path.is_dir():
        pdfs = sorted(input_path.glob("*.pdf"))
    else:
        pdfs = [input_path]

    if not pdfs:
        print(f"No PDF files found in {input_path}")
        return

    for pdf in pdfs:
        print(f"Converting {pdf.name} ...")

        # Generate markdown
        md = pdf_to_markdown(pdf, enable_ocr=not args.no_ocr)

        # Determine output path
        if args.output_dir:
            output_dir = Path(args.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            out = output_dir / (pdf.stem + ".md")
        else:
            out = pdf.parent / (pdf.stem + ".md")

        save_markdown(md, out)


def inspect_pdfs(args: argparse.Namespace) -> None:
    """Inspect PDF(s) and extract metadata as JSON."""
    input_path = Path(args.path)

    # Collect PDFs
    if input_path.is_dir():
        pdfs = sorted(input_path.glob("*.pdf"))
    else:
        pdfs = [input_path]

    if not pdfs:
        print(f"No PDF files found in {input_path}")
        return

    for pdf in pdfs:
        print(f"Inspecting {pdf.name} ...")

        # Determine output directory
        if args.output_dir:
            output_dir = Path(args.output_dir)
        else:
            output_dir = pdf.parent

        inspect_and_save(pdf, output_dir)


if __name__ == "__main__":
    main()
