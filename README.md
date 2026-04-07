# mmpdfkit

Myanmar PDF inspection and Unicode conversion toolkit.

## Status

Steps 1-4 completed: PDF inspection, Unicode conversion, layout reconstruction, and Markdown generation. OCR support added for scanned documents.

## Install

```bash
# Standard install (as library + CLI)
pip install -e ".[dev]"

# With OCR support
pip install -e ".[dev,ocr]"

# Set up pre-commit hooks (runs ruff linting and formatting on commit)
pre-commit install
```

## Usage

### Quick Start

```bash
# Convert PDF to Markdown (output next to input)
mmpdfkit example.pdf          # → example.md

# Convert all PDFs in a directory
mmpdfkit samples/             # → all .md files in same dir

# Skip OCR for scanned documents
mmpdfkit example.pdf --no-ocr

# Custom output directory
mmpdfkit example.pdf --output-dir ./out/
```

### Inspect PDF Metadata

```bash
# Extract font/text metadata as JSON
mmpdfkit inspect example.pdf    # → example_inspection.json

# Inspect all PDFs in directory
mmpdfkit inspect samples/
```

### One-Shot Usage (No Install)

```bash
# Run directly with uv (fastest)
uvx mmpdfkit example.pdf
```

### Library Usage

```python
from mmpdfkit import pdf_to_markdown, inspect_pdf

# Convert PDF to markdown string
md = pdf_to_markdown("example.pdf")

# Inspect PDF metadata
inspection = inspect_pdf("example.pdf")
```

### Advanced: OCR Configuration

Scanned PDFs are automatically processed with OCR (when paddleocr is installed).

**Optional configuration** at `~/.mmpdfkit/config.yaml`:

```yaml
enable_ocr: false  # Set to false to disable OCR by default
```

### Developer Usage

```bash
# Run as module (for development/debugging)
python -m mmpdfkit.markdown samples/example.pdf
python -m mmpdfkit.pdf_inspector samples/example.pdf
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
