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

### As a CLI Tool (Recommended)

**With full OCR support for scanned PDFs:**
```bash
uv tool install "mmpdfkit[ocr]"
```

**Without OCR (faster, for digital PDFs only):**
```bash
uv tool install mmpdfkit
```

Then use the `mmpdfkit` command:
```bash
mmpdfkit example.pdf              # Convert to Markdown
mmpdfkit inspect example.pdf      # Extract metadata as JSON
```

### As a Python Library

**Standard install:**
```bash
pip install mmpdfkit
```

**With OCR support:**
```bash
pip install "mmpdfkit[ocr]"
```

### For Development

```bash
git clone https://github.com/kaungsithu/mmpdfkit.git
cd mmpdfkit
pip install -e ".[dev,ocr]"
pre-commit install
```

## Usage

### CLI Examples

After installing with `uv tool install "mmpdfkit[ocr]"`:

```bash
# Convert PDF to Markdown (output next to input)
mmpdfkit example.pdf                        # → example.md

# Convert all PDFs in a directory
mmpdfkit samples/                           # → all .md files in same dir

# Save to custom output directory
mmpdfkit example.pdf --output-dir ./out/

# Disable OCR for faster processing (digital PDFs)
mmpdfkit example.pdf --no-ocr
```

### Inspect PDF Metadata

```bash
# Extract font/text metadata as JSON
mmpdfkit inspect example.pdf    # → example_inspection.json

# Inspect all PDFs in directory
mmpdfkit inspect samples/
```

### One-Shot Usage (No Install Required)

Use `uvx` to run mmpdfkit without installing it globally:

```bash
# Without OCR (fastest)
uvx mmpdfkit example.pdf

# With OCR for scanned PDFs
uvx --with paddleocr mmpdfkit example.pdf
```

> **Tip:** For repeated use, `uv tool install` is faster than `uvx` since it caches the installation.

### Library Usage

```python
from mmpdfkit import pdf_to_markdown, inspect_pdf

# Convert PDF to markdown string
md = pdf_to_markdown("example.pdf")

# Inspect PDF metadata
inspection = inspect_pdf("example.pdf")
```

### OCR Support

When installed with `[ocr]` extra, scanned PDFs are automatically processed with optical character recognition.

**Disable OCR by default** (optional configuration at `~/.mmpdfkit/config.yaml`):
```yaml
enable_ocr: false
```

Or use `--no-ocr` flag for individual conversions:
```bash
mmpdfkit scanned.pdf --no-ocr
```

### Running from Source (Development)

After cloning and installing with `pip install -e ".[dev,ocr]"`:

```bash
# CLI (same as installed version)
mmpdfkit example.pdf
mmpdfkit inspect example.pdf
```

## Testing

Run the test suite:

```bash
pytest tests/ -v
```

**Test fixture:** `test-pdfs/test.pdf` is a minimal 3-page fixture combining sample pages from various Myanmar PDFs (digital typeset + scanned pages) for testing both text extraction and OCR pipelines.

