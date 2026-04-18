"""Tests for CLI module."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from mmpdfkit.cli import convert_pdfs, inspect_pdfs


def test_convert_single_pdf_default_output():
    """Single PDF converts into a per-PDF sub-directory next to the input file."""
    pdf_path = Path("test_convert.pdf")

    args = MagicMock()
    args.path = pdf_path
    args.output_dir = None
    args.no_ocr = False
    args.include_images = False

    with patch("mmpdfkit.cli._collect_pdfs") as mock_collect:
        with patch("mmpdfkit.cli.pdf_to_markdown") as mock_convert:
            with patch("mmpdfkit.cli.save_markdown") as mock_save:
                with patch.object(Path, "mkdir"):
                    mock_collect.return_value = [pdf_path]
                    mock_convert.return_value = "# Test Markdown"

                    convert_pdfs(args)

                    # Verify pdf_to_markdown was called with correct args
                    mock_convert.assert_called_once()
                    call_args = mock_convert.call_args
                    assert call_args[0][0] == pdf_path
                    assert call_args[1]["enable_ocr"] is True

                    # Output is {parent}/{stem}/{stem}.md
                    mock_save.assert_called_once()
                    output_call = mock_save.call_args
                    expected = pdf_path.parent / "test_convert" / "test_convert.md"
                    assert output_call[0][1] == expected


def test_convert_with_output_dir():
    """Custom output directory is respected."""
    pdf_path = Path("test_convert_outdir.pdf")
    output_dir = Path("/tmp/mmpdfkit_test_out")

    args = MagicMock()
    args.path = pdf_path
    args.output_dir = str(output_dir)
    args.no_ocr = False
    args.include_images = False

    with patch("mmpdfkit.cli._collect_pdfs") as mock_collect:
        with patch("mmpdfkit.cli.pdf_to_markdown") as mock_convert:
            with patch("mmpdfkit.cli.save_markdown") as mock_save:
                with patch.object(Path, "mkdir"):
                    mock_collect.return_value = [pdf_path]
                    mock_convert.return_value = "# Test"

                    convert_pdfs(args)

                    # Output should be in {output_dir}/{stem}/{stem}.md
                    mock_save.assert_called_once()
                    output_call = mock_save.call_args
                    expected = output_dir / "test_convert_outdir" / "test_convert_outdir.md"
                    assert output_call[0][1] == expected


def test_convert_no_ocr_flag():
    """--no-ocr flag disables OCR."""
    pdf_path = Path("test_no_ocr.pdf")

    args = MagicMock()
    args.path = pdf_path
    args.output_dir = None
    args.no_ocr = True
    args.include_images = False

    with patch("mmpdfkit.cli._collect_pdfs") as mock_collect:
        with patch("mmpdfkit.cli.pdf_to_markdown") as mock_convert:
            with patch("mmpdfkit.cli.save_markdown"):
                with patch.object(Path, "mkdir"):
                    mock_collect.return_value = [pdf_path]
                    mock_convert.return_value = ""

                    convert_pdfs(args)

                    # enable_ocr should be False
                    call_args = mock_convert.call_args
                    assert call_args[1]["enable_ocr"] is False


def test_inspect_single_pdf_default_output():
    """Single PDF inspection outputs to same directory."""
    pdf_path = Path("test_inspect.pdf")

    args = MagicMock()
    args.path = pdf_path
    args.output_dir = None

    with patch("mmpdfkit.cli._collect_pdfs") as mock_collect:
        with patch("mmpdfkit.cli.inspect_and_save") as mock_inspect:
            mock_collect.return_value = [pdf_path]

            inspect_pdfs(args)

            # Verify inspect_and_save called with correct args
            mock_inspect.assert_called_once()
            call_args = mock_inspect.call_args
            assert call_args[0][0] == pdf_path
            assert call_args[0][1] == pdf_path.parent


def test_inspect_with_output_dir():
    """Custom output directory is respected for inspect."""
    pdf_path = Path("test_inspect_outdir.pdf")
    output_dir = Path("/tmp/mmpdfkit_test_inspect")

    args = MagicMock()
    args.path = pdf_path
    args.output_dir = str(output_dir)

    with patch("mmpdfkit.cli._collect_pdfs") as mock_collect:
        with patch("mmpdfkit.cli.inspect_and_save") as mock_inspect:
            mock_collect.return_value = [pdf_path]

            inspect_pdfs(args)

            # Output dir should be custom dir
            call_args = mock_inspect.call_args
            assert call_args[0][1] == output_dir


def test_convert_directory_finds_all_pdfs():
    """Directory input processes all PDFs."""
    pdf1 = Path("file1.pdf")
    pdf2 = Path("file2.pdf")

    args = MagicMock()
    args.path = Path("/tmp/test")
    args.output_dir = None
    args.no_ocr = False
    args.include_images = False

    with patch("mmpdfkit.cli._collect_pdfs") as mock_collect:
        with patch("mmpdfkit.cli.pdf_to_markdown") as mock_convert:
            with patch("mmpdfkit.cli.save_markdown") as mock_save:
                with patch.object(Path, "mkdir"):
                    mock_collect.return_value = [pdf1, pdf2]
                    mock_convert.return_value = "# Test"

                    convert_pdfs(args)

                    # Should be called twice (once per PDF)
                    assert mock_convert.call_count == 2
                    assert mock_save.call_count == 2


def test_no_pdfs_found():
    """Graceful handling when no PDFs found."""
    empty_dir = Path(tempfile.gettempdir()) / "mmpdfkit_empty"
    empty_dir.mkdir(exist_ok=True)

    try:
        args = MagicMock()
        args.path = empty_dir
        args.output_dir = None
        args.no_ocr = False
        args.include_images = False

        with patch("mmpdfkit.cli.pdf_to_markdown") as mock_convert:
            with patch("mmpdfkit.cli.save_markdown"):
                with patch("builtins.print"):
                    convert_pdfs(args)

                    # Should not call conversion
                    mock_convert.assert_not_called()
    finally:
        empty_dir.rmdir()
