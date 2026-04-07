"""Tests for CLI module."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import fitz
from mmpdfkit.cli import convert_pdfs, inspect_pdfs


def make_test_pdf(filename: str) -> Path:
    """Create a test PDF and return its path."""
    doc = fitz.open()
    doc.new_page(width=595, height=842)
    doc[-1].insert_text((72, 100), "Test content", fontname="helv", fontsize=12)
    pdf_bytes = doc.tobytes()
    doc.close()

    temp_file = Path(tempfile.gettempdir()) / filename
    temp_file.write_bytes(pdf_bytes)
    return temp_file


def test_convert_single_pdf_default_output():
    """Single PDF converts to same directory as input."""
    pdf_path = make_test_pdf("test_convert.pdf")

    try:
        args = MagicMock()
        args.path = pdf_path
        args.output_dir = None
        args.no_ocr = False

        with patch("mmpdfkit.cli.pdf_to_markdown") as mock_convert:
            with patch("mmpdfkit.cli.save_markdown") as mock_save:
                mock_convert.return_value = "# Test Markdown"

                convert_pdfs(args)

                # Verify pdf_to_markdown was called with correct args
                mock_convert.assert_called_once()
                call_args = mock_convert.call_args
                assert call_args[0][0] == pdf_path
                assert call_args[1]["enable_ocr"] is True

                # Verify output path is next to PDF, not in ./output
                mock_save.assert_called_once()
                output_call = mock_save.call_args
                assert output_call[0][1] == pdf_path.parent / "test_convert.md"
    finally:
        pdf_path.unlink()


def test_convert_with_output_dir():
    """Custom output directory is respected."""
    pdf_path = make_test_pdf("test_convert_outdir.pdf")
    output_dir = Path(tempfile.gettempdir()) / "mmpdfkit_test_out"

    try:
        args = MagicMock()
        args.path = pdf_path
        args.output_dir = str(output_dir)
        args.no_ocr = False

        with patch("mmpdfkit.cli.pdf_to_markdown") as mock_convert:
            with patch("mmpdfkit.cli.save_markdown") as mock_save:
                mock_convert.return_value = "# Test"

                convert_pdfs(args)

                # Output should be in custom dir
                mock_save.assert_called_once()
                output_call = mock_save.call_args
                assert output_call[0][1] == output_dir / "test_convert_outdir.md"
    finally:
        pdf_path.unlink()
        if output_dir.exists():
            output_dir.rmdir()


def test_convert_no_ocr_flag():
    """--no-ocr flag disables OCR."""
    pdf_path = make_test_pdf("test_no_ocr.pdf")

    try:
        args = MagicMock()
        args.path = pdf_path
        args.output_dir = None
        args.no_ocr = True

        with patch("mmpdfkit.cli.pdf_to_markdown") as mock_convert:
            with patch("mmpdfkit.cli.save_markdown"):
                mock_convert.return_value = ""

                convert_pdfs(args)

                # enable_ocr should be False
                call_args = mock_convert.call_args
                assert call_args[1]["enable_ocr"] is False
    finally:
        pdf_path.unlink()


def test_inspect_single_pdf_default_output():
    """Single PDF inspection outputs to same directory."""
    pdf_path = make_test_pdf("test_inspect.pdf")

    try:
        args = MagicMock()
        args.path = pdf_path
        args.output_dir = None

        with patch("mmpdfkit.cli.inspect_and_save") as mock_inspect:
            inspect_pdfs(args)

            # Verify inspect_and_save called with correct args
            mock_inspect.assert_called_once()
            call_args = mock_inspect.call_args
            assert call_args[0][0] == pdf_path
            assert call_args[0][1] == pdf_path.parent
    finally:
        pdf_path.unlink()


def test_inspect_with_output_dir():
    """Custom output directory is respected for inspect."""
    pdf_path = make_test_pdf("test_inspect_outdir.pdf")
    output_dir = Path(tempfile.gettempdir()) / "mmpdfkit_test_inspect"

    try:
        args = MagicMock()
        args.path = pdf_path
        args.output_dir = str(output_dir)

        with patch("mmpdfkit.cli.inspect_and_save") as mock_inspect:
            inspect_pdfs(args)

            # Output dir should be custom dir
            call_args = mock_inspect.call_args
            assert call_args[0][1] == output_dir
    finally:
        pdf_path.unlink()


def test_convert_directory_finds_all_pdfs():
    """Directory input processes all PDFs."""
    temp_dir = Path(tempfile.gettempdir()) / "mmpdfkit_test_dir"
    temp_dir.mkdir(exist_ok=True)

    pdf1 = make_test_pdf(str(temp_dir / "file1.pdf"))
    pdf2 = make_test_pdf(str(temp_dir / "file2.pdf"))

    try:
        args = MagicMock()
        args.path = temp_dir
        args.output_dir = None
        args.no_ocr = False

        with patch("mmpdfkit.cli.pdf_to_markdown") as mock_convert:
            with patch("mmpdfkit.cli.save_markdown") as mock_save:
                mock_convert.return_value = "# Test"

                convert_pdfs(args)

                # Should be called twice (once per PDF)
                assert mock_convert.call_count == 2
                assert mock_save.call_count == 2
    finally:
        pdf1.unlink()
        pdf2.unlink()
        temp_dir.rmdir()


def test_no_pdfs_found():
    """Graceful handling when no PDFs found."""
    empty_dir = Path(tempfile.gettempdir()) / "mmpdfkit_empty"
    empty_dir.mkdir(exist_ok=True)

    try:
        args = MagicMock()
        args.path = empty_dir
        args.output_dir = None
        args.no_ocr = False

        with patch("mmpdfkit.cli.pdf_to_markdown") as mock_convert:
            with patch("mmpdfkit.cli.save_markdown"):
                with patch("builtins.print"):
                    convert_pdfs(args)

                    # Should not call conversion
                    mock_convert.assert_not_called()
    finally:
        empty_dir.rmdir()
