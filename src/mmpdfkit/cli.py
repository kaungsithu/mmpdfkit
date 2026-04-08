"""Command-line interface for mmpdfkit."""

import argparse
import platform
import shutil
import subprocess
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


def _detect_linux_distro() -> str:
    """Return 'debian', 'arch', 'fedora', or 'unknown'."""
    try:
        text = Path("/etc/os-release").read_text()
        if any(x in text for x in ("debian", "ubuntu", "mint", "pop")):
            return "debian"
        if "arch" in text or "manjaro" in text:
            return "arch"
        if any(x in text for x in ("fedora", "rhel", "centos", "rocky")):
            return "fedora"
    except FileNotFoundError:
        pass
    # Fallback: check for package managers
    if shutil.which("apt"):
        return "debian"
    if shutil.which("pacman"):
        return "arch"
    if shutil.which("dnf") or shutil.which("yum"):
        return "fedora"
    return "unknown"


def _get_install_steps() -> list[dict]:
    """
    Return a list of install steps for the current platform.

    Each step is {"desc": str, "cmd": list[str], "requires_elevation": bool}.
    """
    os_name = platform.system()

    if os_name == "Darwin":
        has_brew = bool(shutil.which("brew"))
        if not has_brew:
            return [
                {
                    "desc": "Install Homebrew (package manager for macOS)",
                    "cmd": [
                        "/bin/bash",
                        "-c",
                        "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)",
                    ],
                    "requires_elevation": False,
                    "note": "Visit https://brew.sh if you prefer to install manually",
                },
                {
                    "desc": "Install Tesseract with Myanmar language data",
                    "cmd": ["brew", "install", "tesseract", "tesseract-lang"],
                    "requires_elevation": False,
                },
            ]
        return [
            {
                "desc": "Install Tesseract with Myanmar language data",
                "cmd": ["brew", "install", "tesseract", "tesseract-lang"],
                "requires_elevation": False,
            }
        ]

    if os_name == "Windows":
        has_winget = bool(shutil.which("winget"))
        if has_winget:
            return [
                {
                    "desc": "Install Tesseract (UB Mannheim build with all languages)",
                    "cmd": ["winget", "install", "UB-Mannheim.TesseractOCR"],
                    "requires_elevation": True,
                    "note": "Run in an Administrator terminal, or download manually from "
                    "https://github.com/UB-Mannheim/tesseract/wiki",
                },
            ]
        return [
            {
                "desc": "Download Tesseract installer",
                "cmd": [],
                "requires_elevation": False,
                "note": "winget not found. Download from: "
                "https://github.com/UB-Mannheim/tesseract/wiki\n"
                "  During install, check 'Additional language data' → Myanmar",
            }
        ]

    # Linux
    distro = _detect_linux_distro()

    if distro == "debian":
        return [
            {
                "desc": "Install Tesseract with Myanmar language pack",
                "cmd": ["sudo", "apt", "install", "-y", "tesseract-ocr", "tesseract-ocr-mya"],
                "requires_elevation": True,
            }
        ]
    if distro == "arch":
        return [
            {
                "desc": "Install Tesseract with Myanmar language data",
                "cmd": ["sudo", "pacman", "-S", "--noconfirm", "tesseract", "tesseract-data-mya"],
                "requires_elevation": True,
            }
        ]
    if distro == "fedora":
        return [
            {
                "desc": "Install Tesseract",
                "cmd": ["sudo", "dnf", "install", "-y", "tesseract"],
                "requires_elevation": True,
            },
            {
                "desc": "Install Myanmar language pack",
                "cmd": ["sudo", "dnf", "install", "-y", "tesseract-langpack-mya"],
                "requires_elevation": True,
            },
        ]

    # Unknown Linux
    return [
        {
            "desc": "Install Tesseract",
            "cmd": [],
            "requires_elevation": False,
            "note": "Could not detect your package manager. See: "
            "https://tesseract-ocr.github.io/tessdoc/Installation.html\n"
            "  Ensure the Myanmar ('mya') language pack is included.",
        }
    ]


def _ocr_already_installed() -> bool:
    """Return True if tesseract is installed with Myanmar support."""
    if not shutil.which("tesseract"):
        return False
    try:
        result = subprocess.run(
            ["tesseract", "--list-langs"],
            capture_output=True,
            text=True,
        )
        return "mya" in result.stdout + result.stderr
    except Exception:
        return False


def install_ocr(args: argparse.Namespace) -> None:
    """Show or run OCR installation instructions."""
    if _ocr_already_installed():
        print("✓ OCR (Tesseract + Myanmar) is already installed and ready.")
        return

    steps = _get_install_steps()

    print("To enable OCR for scanned Burmese PDFs, install Tesseract:\n")

    runnable_steps = []
    for i, step in enumerate(steps, 1):
        print(f"  Step {i}: {step['desc']}")
        if step["cmd"]:
            print(f"    $ {' '.join(step['cmd'])}")
            if step.get("requires_elevation") and platform.system() != "Windows":
                print("    (requires sudo / administrator privileges)")
            runnable_steps.append(step)
        if step.get("note"):
            for line in step["note"].split("\n"):
                print(f"    {line}")
        print()

    if not args.run:
        if runnable_steps:
            print("Run with --run to execute these commands automatically.")
        return

    # --- Execute mode ---
    if not runnable_steps:
        print("No commands to run automatically for your platform. See instructions above.")
        return

    print("Running install commands...\n")
    for step in runnable_steps:
        print(f"→ {step['desc']}")
        print(f"  $ {' '.join(step['cmd'])}\n")
        try:
            subprocess.run(step["cmd"], check=True)
            print("  ✓ Done\n")
        except subprocess.CalledProcessError as e:
            print(f"  ✗ Failed (exit code {e.returncode})", file=sys.stderr)
            print("  Try running the command manually.", file=sys.stderr)
            sys.exit(1)
        except FileNotFoundError:
            print(f"  ✗ Command not found: {step['cmd'][0]}", file=sys.stderr)
            sys.exit(1)

    if _ocr_already_installed():
        print("✓ OCR installed successfully. You can now convert scanned PDFs:")
        print("  mmpdfkit your_file.pdf")
    else:
        print("Installation may require a shell restart or PATH update.")
        print("Verify with: tesseract --list-langs")


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

    output_dir = _resolve_output_dir(args.output_dir)
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    for pdf in pdfs:
        print(f"Converting {pdf.name} ...")

        try:
            md = pdf_to_markdown(pdf, enable_ocr=not args.no_ocr)
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
