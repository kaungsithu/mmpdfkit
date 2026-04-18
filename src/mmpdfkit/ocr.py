"""
ocr.py — CRNN-based OCR for scanned Myanmar PDF pages.

Uses a lightweight CRNN + CTC model (~8 MB INT8 ONNX) trained on 7.6M real
scanned Myanmar document images. The model is downloaded from HuggingFace on
first use and cached in ~/.cache/mmpdfkit/.

Install optional dependencies: pip install mmpdfkit[ocr]
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Vocabulary — must stay in sync with ocr-training/training/dataset.py
# ---------------------------------------------------------------------------
_MYANMAR_BASIC = "".join(chr(c) for c in range(0x1000, 0x109F + 1))
_MYANMAR_EXTENDED = "".join(chr(c) for c in range(0xAA60, 0xAA7F + 1))
_MYANMAR_PUNCTUATION = "".join(chr(c) for c in range(0x104A, 0x104F + 1))
_ENGLISH = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
_PUNCTUATION = ".,!?;:()[]{}\"'/- "
_BLANK = "<blank>"

_VOCAB = sorted(set(
    [_BLANK] + list(_ENGLISH) + list(_PUNCTUATION) +
    list(_MYANMAR_BASIC) + list(_MYANMAR_EXTENDED) + list(_MYANMAR_PUNCTUATION)
))
_CHAR_TO_IDX: dict[str, int] = {c: i for i, c in enumerate(_VOCAB)}
_IDX_TO_CHAR: dict[int, str] = {i: c for c, i in _CHAR_TO_IDX.items()}
_BLANK_IDX: int = _CHAR_TO_IDX[_BLANK]  # = 22
NUM_CLASSES: int = len(_VOCAB)           # = 272

# ---------------------------------------------------------------------------
# Model download
# ---------------------------------------------------------------------------
# Model hosted at: https://huggingface.co/ksithu/myanmar-crnn-ocr
_MODEL_URL = (
    "https://huggingface.co/ksithu/myanmar-crnn-ocr/resolve/main/mmpdfkit_crnn_int8.onnx"
)
_CACHE_DIR = Path.home() / ".cache" / "mmpdfkit"
_MODEL_FILENAME = "mmpdfkit_crnn_int8.onnx"


def _model_path() -> Path:
    return _CACHE_DIR / _MODEL_FILENAME


def model_is_cached() -> bool:
    """Return True if the CRNN ONNX model has already been downloaded."""
    return _model_path().exists()


def _ensure_model() -> Path:
    """Download model to cache if not already present."""
    path = _model_path()
    if path.exists():
        return path

    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading Myanmar OCR model to {path} ...", file=sys.stderr)
    try:
        urllib.request.urlretrieve(_MODEL_URL, path)
    except Exception as e:
        path.unlink(missing_ok=True)
        raise RuntimeError(
            f"Failed to download OCR model from {_MODEL_URL}: {e}\n"
            "Check your internet connection, or download manually and place at:\n"
            f"  {path}"
        ) from e
    print("Download complete.", file=sys.stderr)
    return path


# ---------------------------------------------------------------------------
# Inference helpers
# ---------------------------------------------------------------------------

def _decode_ctc(indices: list[int]) -> str:
    """Greedy CTC decode: collapse repeats and remove blanks."""
    result = []
    prev = None
    for idx in indices:
        if idx == _BLANK_IDX:
            prev = None
        elif idx != prev:
            result.append(_IDX_TO_CHAR.get(idx, ""))
            prev = idx
        else:
            prev = idx
    return "".join(result)


def _load_session():
    """Load (or return cached) ONNX Runtime inference session."""
    try:
        import onnxruntime as ort
    except ImportError:
        raise ImportError(
            "onnxruntime is required for OCR. Install with: pip install mmpdfkit[ocr]"
        )
    model_path = _ensure_model()
    opts = ort.SessionOptions()
    opts.inter_op_num_threads = 2
    opts.intra_op_num_threads = 2
    return ort.InferenceSession(str(model_path), opts, providers=["CPUExecutionProvider"])


_session = None  # lazy singleton


def _get_session():
    global _session
    if _session is None:
        _session = _load_session()
    return _session


def _run_ocr_on_crop(crop_gray, session) -> str:
    """Run CRNN inference on a single grayscale line crop (H, W) uint8."""
    import cv2
    import numpy as np

    h, w = crop_gray.shape
    # Normalise to 32px tall, double width — matches training preprocessing
    if h != 32:
        new_w = max(1, round(w * 32 / h))
        crop_gray = cv2.resize(crop_gray, (new_w, 32), interpolation=cv2.INTER_LANCZOS4)
    crop_gray = cv2.resize(crop_gray, (crop_gray.shape[1] * 2, 32), interpolation=cv2.INTER_LANCZOS4)

    arr = crop_gray.astype(np.float32) / 255.0
    x = arr[np.newaxis, np.newaxis, :, :]  # (1, 1, 32, W)

    logits = session.run(["output"], {"input": x})[0]  # (1, W', 272)
    indices = logits[0].argmax(axis=1).tolist()         # (W',)
    return _decode_ctc(indices)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def ocr_page_spans(page_gray, page_width: float) -> list[dict]:
    """
    Run OCR on a single grayscale page image (already rendered, uint8 numpy array).

    Args:
        page_gray: Grayscale page image (H, W) uint8.
        page_width: PDF page width in points (used to scale bbox coordinates).

    Returns:
        List of span dicts matching pdf_inspector output format.
    """
    import numpy as np

    from mmpdfkit.line_detector import extract_line_images

    # page_gray may have been rendered at 2× — scale back to PDF coords
    scale = page_width / page_gray.shape[1]

    session = _get_session()
    line_crops = extract_line_images(page_gray)
    spans: list[dict] = []

    for y0, y1, crop in line_crops:
        text = _run_ocr_on_crop(crop, session).strip()
        if not text:
            continue
        spans.append({
            "text": text,
            "font_name": "ocr-crnn",
            "font_encoding": "unicode",
            "font_size": 12.0,
            "is_bold": False,
            "is_italic": False,
            "bbox": [0.0, y0 * scale, page_width, y1 * scale],
        })

    return spans


def extract_and_ocr(
    pdf_path: Path,
    enable_ocr: bool = True,
) -> list[list[dict[str, Any]]]:
    """
    Extract text from a scanned PDF using CRNN OCR.

    Renders each page to a grayscale image, detects text lines via horizontal
    projection, and runs the CRNN model on each line crop.

    Args:
        pdf_path: Path to the PDF file.
        enable_ocr: If False, raises ValueError immediately (user disabled OCR).

    Returns:
        List of per-page span lists matching pdf_inspector output format.

    Raises:
        ValueError: If enable_ocr is False.
        ImportError: If onnxruntime, pillow, or opencv-python-headless is missing.
        FileNotFoundError: If pdf_path does not exist.
        RuntimeError: If model download fails.
    """
    if not enable_ocr:
        raise ValueError("OCR disabled (enable_ocr=False)")

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    try:
        import numpy as np  # noqa: F401 — triggers ImportError early if missing
    except ImportError as e:
        raise ImportError(
            f"Missing dependency for OCR ({e}). "
            "Install with: pip install mmpdfkit[ocr]"
        ) from e

    import fitz

    doc = fitz.open(str(pdf_path))
    pages_spans: list[list[dict[str, Any]]] = []

    try:
        for page in doc:
            # Render at 2x resolution for better OCR accuracy
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), colorspace=fitz.csGRAY)
            page_gray = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width
            )
            pages_spans.append(ocr_page_spans(page_gray, page.rect.width))
    finally:
        doc.close()

    return pages_spans
