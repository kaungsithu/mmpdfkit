"""
layout.py — Reconstruct reading order layout from PDF text spans.

PDF spans are emitted in painting order (not reading order) and have no
paragraph structure. This module groups spans into lines by Y-coordinate
proximity, then groups lines into paragraphs by inter-line gap size.

Headings are detected when a line's dominant font size is larger than the
median body size by a configurable ratio.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field


@dataclass
class Line:
    """A horizontal run of spans on the same vertical position."""

    spans: list[dict]
    y_top: float
    y_bottom: float

    @property
    def text(self) -> str:
        """Spans sorted left-to-right, joined with a space."""
        sorted_spans = sorted(self.spans, key=lambda s: s["bbox"][0])
        parts = [s["unicode_text"] for s in sorted_spans if s["unicode_text"].strip()]
        return " ".join(parts)

    @property
    def font_size(self) -> float:
        """Most common font size among the spans in this line."""
        if not self.spans:
            return 0.0
        sizes = [s["font_size"] for s in self.spans]
        return max(set(sizes), key=sizes.count)

    @property
    def height(self) -> float:
        return self.y_bottom - self.y_top


@dataclass
class Paragraph:
    """One or more consecutive lines treated as a single logical unit."""

    lines: list[Line] = field(default_factory=list)
    is_heading: bool = False
    heading_level: int = 0  # 1=h1, 2=h2, 3=h3; 0=body text

    @property
    def text(self) -> str:
        return "\n".join(line.text for line in self.lines if line.text.strip())


def group_spans_into_lines(spans: list[dict], y_tolerance: float = 4.0) -> list[Line]:
    """
    Group spans into lines by Y-coordinate proximity.

    Spans whose vertical midpoints are within y_tolerance points of the
    current line's midpoint are added to that line. A new line starts when
    the gap is larger.

    Args:
        spans: Span dicts that must have a "bbox" [x0,y0,x1,y1] field.
        y_tolerance: Max vertical distance (points) to consider same line.

    Returns:
        Lines sorted top-to-bottom.
    """
    if not spans:
        return []

    sorted_spans = sorted(spans, key=lambda s: (s["bbox"][1], s["bbox"][0]))

    lines: list[Line] = []
    bucket = [sorted_spans[0]]
    ref_y = (sorted_spans[0]["bbox"][1] + sorted_spans[0]["bbox"][3]) / 2

    for span in sorted_spans[1:]:
        mid_y = (span["bbox"][1] + span["bbox"][3]) / 2
        if abs(mid_y - ref_y) <= y_tolerance:
            bucket.append(span)
        else:
            y_top = min(s["bbox"][1] for s in bucket)
            y_bottom = max(s["bbox"][3] for s in bucket)
            lines.append(Line(spans=bucket, y_top=y_top, y_bottom=y_bottom))
            bucket = [span]
            ref_y = mid_y

    if bucket:
        y_top = min(s["bbox"][1] for s in bucket)
        y_bottom = max(s["bbox"][3] for s in bucket)
        lines.append(Line(spans=bucket, y_top=y_top, y_bottom=y_bottom))

    return lines


def group_lines_into_paragraphs(
    lines: list[Line],
    gap_factor: float = 1.4,
    heading_size_ratio: float = 1.15,
) -> list[Paragraph]:
    """
    Group lines into paragraphs and detect headings.

    A new paragraph starts when the vertical gap between two lines exceeds
    gap_factor * the previous line's height. Headings are lines whose font
    size is at least heading_size_ratio * the median body font size.

    Args:
        lines: Output of group_spans_into_lines().
        gap_factor: Gap threshold multiplier.
        heading_size_ratio: Font-size ratio to trigger heading detection.

    Returns:
        List of Paragraphs in reading order.
    """
    if not lines:
        return []

    # Estimate body font size from median (ignores very large or very small outliers)
    all_sizes = [line.font_size for line in lines if line.font_size > 0]
    body_size = statistics.median(all_sizes) if all_sizes else 12.0

    paragraphs: list[Paragraph] = []
    current: list[Line] = [lines[0]]

    for i in range(1, len(lines)):
        prev = lines[i - 1]
        curr = lines[i]
        gap = curr.y_top - prev.y_bottom
        threshold = max(prev.height * gap_factor, 2.0)

        if gap > threshold:
            para = _make_paragraph(current, body_size, heading_size_ratio)
            paragraphs.append(para)
            current = [curr]
        else:
            current.append(curr)

    if current:
        paragraphs.append(_make_paragraph(current, body_size, heading_size_ratio))

    return paragraphs


def _make_paragraph(lines: list[Line], body_size: float, ratio: float) -> Paragraph:
    para = Paragraph(lines=lines)
    dominant = max((line.font_size for line in lines), default=0.0)
    if dominant >= body_size * ratio:
        para.is_heading = True
        r = dominant / body_size
        if r >= 1.8:
            para.heading_level = 1
        elif r >= 1.4:
            para.heading_level = 2
        else:
            para.heading_level = 3
    return para


def reconstruct_page(page: dict) -> list[Paragraph]:
    """
    Full layout reconstruction for a single converted page dict.

    The page must have spans with a "unicode_text" field (run
    converter.convert_inspection() first).

    Args:
        page: Page dict from converter.convert_inspection() output.

    Returns:
        List of Paragraphs in reading order.
    """
    spans = [s for s in page["spans"] if s.get("unicode_text", "").strip()]
    lines = group_spans_into_lines(spans)
    return group_lines_into_paragraphs(lines)
