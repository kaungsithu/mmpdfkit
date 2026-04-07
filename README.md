# mmpdfkit

Myanmar PDF inspection and Unicode conversion toolkit.

## Status

Steps 1-4 completed: PDF inspection, Unicode conversion, layout reconstruction, and Markdown generation. OCR support added for scanned documents.

## Install

```bash
pip install -e ".[dev]"

# Set up pre-commit hooks (runs ruff linting and formatting on commit)
pre-commit install
```

## Usage

### Convert PDF to Markdown

```bash
# Convert a single PDF to Markdown
python -m mmpdfkit.markdown samples/example.pdf

# Convert all PDFs in a directory
python -m mmpdfkit.markdown samples/

# Custom output directory
python -m mmpdfkit.markdown samples/ --output-dir my_output/
```

### OCR for Scanned PDFs

Scanned Myanmar PDFs are automatically processed with OCR when available:

```bash
# Automatic OCR (if paddleocr installed)
python -m mmpdfkit.markdown scanned-doc.pdf

# Skip OCR
python -m mmpdfkit.markdown scanned-doc.pdf --no-ocr
```

**Optional configuration** at `~/.mmpdfkit/config.yaml`:

```yaml
enable_ocr: false  # Set to false to disable OCR by default
```

**Installation with OCR support:**

```bash
pip install mmpdfkit[ocr]
```

### Inspect PDF Metadata

```bash
# Inspect a single PDF
python -m mmpdfkit.pdf_inspector samples/example.pdf

# Inspect all PDFs in a directory
python -m mmpdfkit.pdf_inspector samples/
```

## Testing

Run the test suite:

```bash
pytest tests/ -v
```

**Test fixture:** `test-pdfs/test.pdf` is a minimal 3-page fixture combining sample pages from various Myanmar PDFs (digital typeset + scanned pages) for testing both text extraction and OCR pipelines.

## Roadmap

1. PDF inspection (font metadata extraction) ✓ complete
2. Zawgyi → Unicode conversion ✓ complete
3. Layout reconstruction ✓ complete
4. Markdown generation ✓ complete
5. OCR for scanned documents ✓ complete
