"""Command-line interface for mmpdfkit."""

import argparse
import sys
from pathlib import Path

from mmpdfkit.markdown import pdf_to_markdown, save_markdown
from mmpdfkit.pdf_inspector import inspect_and_save

_SUBCOMMANDS = ("convert", "inspect", "install-ocr")


def main() -> None:
    """Main CLI entry point with subcommands for convert and inspect."""
    # Pre-process args: if first arg looks like a path, prepend "convert"
    args_to_parse = sys.argv[1:]
    if args_to_parse and not args_to_parse[0].startswith("-"):
        first_arg = args_to_parse[0]
        if first_arg not in _SUBCOMMANDS:
            args_to_parse = ["convert", *args_to_parse]

    parser = argparse.ArgumentParser(
        prog="mmpdfkit",
        description="Myanmar PDF inspection, Unicode conversion, and OCR toolkit",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run", required=False)

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

    # Install-OCR command
    install_ocr_parser = subparsers.add_parser(
        "install-ocr",
        help="Show (or run) OCR installation instructions for your platform",
    )
    _add_install_ocr_args(install_ocr_parser)

    # Parse the processed args
    args = parser.parse_args(args_to_parse)

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "convert":
        convert_pdfs(args)
    elif args.command == "inspect":
        inspect_pdfs(args)
    elif args.command == "install-ocr":
        install_ocr(args)
    else:
        parser.print_help()
        sys.exit(1)


def _add_convert_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("path", help="PDF file or directory of PDFs")
    parser.add_argument(
        "--output-dir", default=None, help="Output directory (default: same as input)"
    )
    parser.add_argument("--no-ocr", action="store_true", help="Disable OCR for scanned documents")
    parser.add_argument(
        "--include-images",
        action="store_true",
        help="Save image-only pages as PNG and embed in Markdown",
    )


def _add_inspect_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("path", help="PDF file or directory of PDFs")
    parser.add_argument(
        "--output-dir", default=None, help="Output directory (default: same as input)"
    )


def _add_install_ocr_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--run",
        action="store_true",
        help="Execute the install commands (default: print only)",
    )


def _collect_pdfs(input_path: Path) -> list[Path]:
    """Collect PDFs from a file or directory."""
    if input_path.is_dir():
        return sorted(input_path.glob("*.pdf"))
    return [input_path] if input_path.suffix.lower() == ".pdf" else []


def _resolve_output_dir(output_dir_arg: str | None) -> Path | None:
    """Resolve output directory from CLI argument."""
    return Path(output_dir_arg) if output_dir_arg else None


# ---------------------------------------------------------------------------
# OCR install helpers
# ---------------------------------------------------------------------------

_OCR_PACKAGES = ["onnxruntime>=1.17.0", "pillow>=10.0.0", "opencv-python-headless>=4.8.0"]


def _ocr_deps_installed() -> bool:
    """Return True if all OCR Python packages are importable."""
    try:
        import cv2  # noqa: F401
        import onnxruntime  # noqa: F401
        from PIL import Image  # noqa: F401

        return True
    except ImportError:
        return False


def _model_cached() -> bool:
    from mmpdfkit.ocr import model_is_cached

    return model_is_cached()


def install_ocr(args: argparse.Namespace) -> None:
    """Show OCR status, or install Python OCR dependencies and pre-download the model."""
    import subprocess

    deps_ok = _ocr_deps_installed()
    model_ok = _model_cached()

    if deps_ok and model_ok:
        print("OCR is ready: Python dependencies installed and model cached.")
        return

    if not deps_ok:
        print("OCR Python dependencies are not installed.")
        print(f"  Required packages: {', '.join(_OCR_PACKAGES)}")
        print()
        print("Install with:")
        print("  pip install mmpdfkit[ocr]")
        print()

    if deps_ok and not model_ok:
        print("OCR model not yet downloaded (will be fetched automatically on first use).")
        print()

    if not args.run:
        print("Run with --run to install dependencies and pre-download the model.")
        return

    # --- Execute mode ---
    if not deps_ok:
        print("Installing OCR dependencies...")
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "mmpdfkit[ocr]"],
                check=True,
            )
            print("Dependencies installed.")
        except subprocess.CalledProcessError as e:
            print(f"pip install failed (exit code {e.returncode})", file=sys.stderr)
            sys.exit(1)

    if not model_ok:
        print("Pre-downloading CRNN OCR model...")
        try:
            from mmpdfkit.ocr import _ensure_model

            _ensure_model()
            print("Model downloaded and cached.")
        except RuntimeError as e:
            print(f"Model download failed: {e}", file=sys.stderr)
            sys.exit(1)

    print("OCR is ready. You can now convert scanned PDFs:")
    print("  mmpdfkit your_file.pdf")


# ---------------------------------------------------------------------------
# Convert / Inspect
# ---------------------------------------------------------------------------


def convert_pdfs(args: argparse.Namespace) -> None:
    """Convert PDF(s) to Markdown."""
    input_path = Path(args.path)
    pdfs = _collect_pdfs(input_path)

    if not pdfs:
        print(f"No PDF files found in {input_path}")
        return

    base_out = _resolve_output_dir(args.output_dir) or input_path.parent
    include_images = getattr(args, "include_images", False)

    for pdf in pdfs:
        print(f"Converting {pdf.name} ...")

        try:
            # Per-PDF sub-directory: {base_out}/{pdf_stem}/{pdf_stem}.md
            pdf_out_dir = base_out / pdf.stem
            pdf_out_dir.mkdir(parents=True, exist_ok=True)

            md = pdf_to_markdown(
                pdf,
                enable_ocr=not args.no_ocr,
                output_dir=pdf_out_dir,
                include_images=include_images,
            )
            out = pdf_out_dir / (pdf.stem + ".md")
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

    output_dir = _resolve_output_dir(args.output_dir)

    for pdf in pdfs:
        print(f"Inspecting {pdf.name} ...")

        try:
            out_dir = output_dir if output_dir else pdf.parent
            inspect_and_save(pdf, out_dir)
        except Exception as e:
            print(f"Error inspecting {pdf.name}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
