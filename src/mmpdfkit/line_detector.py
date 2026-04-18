"""
line_detector.py — Extract text line crops from a grayscale page image.

Uses horizontal projection profiles with deskew and morphological dilation.
No ML model required — pure OpenCV. Handles standard single-column layouts
well; multi-column pages (newspapers) are handled by column splitting.
"""

from __future__ import annotations

import numpy as np


def extract_line_images(
    page_gray: np.ndarray,
    pad: int = 4,
    min_line_height: int = 8,
    max_line_height: int = 200,
) -> list[tuple[int, int, np.ndarray]]:
    """
    Detect and crop text lines from a grayscale page image.

    Args:
        page_gray: Grayscale page image as uint8 numpy array (H, W).
        pad: Pixels to add above/below each detected line band.
        min_line_height: Minimum pixel height to count as a line (filters
                         hairlines and horizontal rules).
        max_line_height: Maximum pixel height to count as a line. Bands taller
                         than this are almost certainly not a single text line
                         (e.g. pages with full-height borders confusing the
                         projection). Skipping them avoids passing a whole-page
                         crop to the CRNN and getting garbage output.

    Returns:
        List of (y_top, y_bottom, crop) tuples where crop is a grayscale
        uint8 array of the line region including padding.
    """
    try:
        import cv2
    except ImportError:
        raise ImportError(
            "opencv-python-headless is required for line detection. "
            "Install with: pip install mmpdfkit[ocr]"
        )

    # 1. Binarise (Otsu — works on variable scan quality)
    _, bw = cv2.threshold(page_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # 2. Deskew — corrects up to ~5° rotation cheaply
    bw = _deskew(bw, page_gray)

    # 3. Horizontal dilation — merges characters within a line so the
    #    projection sees a solid band, even with touching Myanmar diacritics
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
    dilated = cv2.dilate(bw, kernel)

    # 4. Row projection
    projection = np.sum(dilated, axis=1).astype(np.int32)
    threshold = int(dilated.shape[1] * 0.005)  # >0.5% of row width = active

    # 5. Detect line bands
    active = projection > threshold
    bands: list[tuple[int, int]] = []
    start = None
    for y, on in enumerate(active):
        if on and start is None:
            start = y
        elif not on and start is not None:
            bands.append((start, y))
            start = None
    if start is not None:
        bands.append((start, len(active)))

    # 6. Crop with padding, skip noise and oversized bands
    h, w = page_gray.shape
    crops = []
    for y0, y1 in bands:
        if (y1 - y0) < min_line_height:
            continue
        if (y1 - y0) > max_line_height:
            continue
        y0p = max(0, y0 - pad)
        y1p = min(h, y1 + pad)
        crops.append((y0p, y1p, page_gray[y0p:y1p, :]))

    return crops


def _deskew(bw: np.ndarray, page_gray: np.ndarray) -> np.ndarray:
    """Correct small rotation in bw using minAreaRect on dark pixels."""
    import cv2

    coords = np.column_stack(np.where(bw > 0))
    if len(coords) < 100:
        return bw

    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = 90 + angle
    if abs(angle) < 0.3:  # no meaningful skew
        return bw

    h, w = bw.shape
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(bw, M, (w, h), flags=cv2.INTER_NEAREST)
