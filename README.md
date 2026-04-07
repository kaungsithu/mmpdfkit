# mmpdfkit

Convert Burmese PDFs to clean, usable Markdown and text for AI applications, data analysis, and vectorization.

## What is mmpdfkit?

**mmpdfkit** solves a critical problem for anyone working with Burmese/Myanmar text: extracting usable content from PDFs with mixed encodings, legacy fonts, and scanned documents.

Burmese PDFs often contain text in multiple non-Unicode encodings (Win Myanmar, Zawgyi) or are entirely scanned. This makes them unsuitable for AI model input, vectorization, or modern text processing pipelines. mmpdfkit automatically:

- **Detects and converts** legacy Myanmar encodings (Win Myanmar, Zawgyi) to proper Unicode
- **Extracts text** with layout preservation via Markdown formatting
- **OCR scans** for documents that are image-based
- **Preserves structure** (headings, paragraphs, spacing) during conversion

### Use Cases

- **AI/LLM contexts** — Clean Burmese text for prompt context or fine-tuning
- **Vectorization** — Prepare PDFs for embedding and vector databases
- **Text analysis** — Linguistic research on Burmese corpora
- **Content migration** — Convert legacy Burmese digital archives to modern formats

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
# Run directly with uv (fastest, no OCR)
uvx mmpdfkit example.pdf

# With OCR support for scanned PDFs
uvx --with paddleocr mmpdfkit example.pdf
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

