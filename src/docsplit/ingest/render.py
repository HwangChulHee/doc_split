"""Turning a page into the image the vision model reads.

The vision path only ever sees a raster, so the one thing that matters is which
way the letters face in that raster. This module decides that from the rendered
pixels instead of from the PDF's ``/Rotate`` field, and records the numbers it
decided on — the same "every judgement carries its evidence" rule the text path
follows.

Why not the metadata: in this dataset the three scanned pages store a
``/Rotate`` that disagrees with the scan, and applying it lays the page on its
side. Trusting the field failed here; distrusting it unconditionally would fail
on the next PDF whose field is right. Neither is a judgement, so we look at the
picture.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass

import pymupdf

PROBE_DPI = 60  # coarse enough to be cheap, fine enough to separate text lines
INK_LEVEL = 160  # an 8-bit gray value below this counts as ink
MIN_INK_RATIO = 0.002  # below this there is not enough on the page to read a direction off
AXIS_MARGIN = 1.5  # how far the winning axis must beat the other to count as decided

# 256-entry translation table: ink -> 1, background -> 0, so a row of the
# raster can be summed at C speed instead of scanned pixel by pixel.
_INK_TABLE = bytes(1 if level < INK_LEVEL else 0 for level in range(256))


@dataclass
class Orientation:
    """The rotation used for a render, and why it was chosen."""

    rotation: int  # what was applied when rendering (0/90/180/270)
    axis: str  # horizontal | vertical | undetermined — the way text runs
    confidence: str  # high | low
    reason: str
    line_scores: dict[str, float]  # candidate rotation -> line-structure score
    ink_ratio: float
    stored_rotation: int  # the /Rotate the file asked for
    unresolved: str | None = None  # what the pixels could not settle

    def to_dict(self) -> dict:
        return asdict(self)


@contextmanager
def rotated(page: pymupdf.Page, rotation: int) -> Iterator[pymupdf.Page]:
    """Draw with `rotation` in place of the stored one, then put the stored one back.

    The same page object is reused afterwards for geometry-based extraction,
    which does depend on the stored value.
    """
    original = page.rotation
    try:
        page.set_rotation(rotation)
        yield page
    finally:
        page.set_rotation(original)


def _row_ink(page: pymupdf.Page, rotation: int, dpi: int) -> tuple[list[int], int, int]:
    """Ink pixels per raster row at `rotation`, plus the raster's width and height."""
    with rotated(page, rotation):
        pixmap = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY)
    flat = pixmap.samples.translate(_INK_TABLE)
    width, stride = pixmap.width, pixmap.stride
    rows = [sum(flat[y * stride : y * stride + width]) for y in range(pixmap.height)]
    return rows, width, pixmap.height


def _line_score(profile: list[int]) -> float:
    """How strongly the row profile alternates between inked rows and empty ones.

    Variance over squared mean — a squared coefficient of variation, so it is
    scale-free and a dense page compares with a sparse one. Text running across
    the rows leaves bands of ink separated by line gaps and scores high; the
    same text seen along the rows smears evenly over every row and scores low.
    """
    if not profile:
        return 0.0
    mean = sum(profile) / len(profile)
    if mean <= 0:
        return 0.0
    variance = sum((value - mean) ** 2 for value in profile) / len(profile)
    return variance / (mean * mean)


def detect_orientation(page: pymupdf.Page, dpi: int = PROBE_DPI) -> Orientation:
    """Choose the rotation that stands the page's text lines upright.

    Two probe renders cover all four candidates. Rotating 180° reverses the row
    profile of the 0° render and 270° reverses that of the 90° render, and
    reversing a profile leaves its variance and mean untouched — so each render
    scores a *pair* of candidates, and no information is lost by not drawing the
    other two.

    That symmetry is also the method's limit: it settles the axis the text runs
    along, never which end of that axis is the top. Upside-down text scores
    exactly like upright text. A measurement of the one candidate feature that
    does differ — where the ink sits inside each line band, since ascenders and
    descenders are not mirror images — separated upright from flipped on only
    65 of 76 real pages here, and got all three of this dataset's scans wrong
    (their dense all-caps paragraphs have almost no descenders). So it is not
    used: the pixels decide the axis, and the up/down half is reported as
    unresolved rather than guessed.

    PyMuPDF offers no help for the pages that need this. Its per-line ``dir``
    vector would give the writing direction outright, but it comes from the text
    layer, and a page reaches the vision path precisely because it has none.
    """
    horizontal_rows, width, height = _row_ink(page, 0, dpi)
    vertical_rows, _, _ = _row_ink(page, 90, dpi)
    ink_ratio = sum(horizontal_rows) / (width * height) if width and height else 0.0
    scores = {"0/180": round(_line_score(horizontal_rows), 3),
              "90/270": round(_line_score(vertical_rows), 3)}
    horizontal, vertical = scores["0/180"], scores["90/270"]

    if ink_ratio < MIN_INK_RATIO:
        return Orientation(
            rotation=0, axis="undetermined", confidence="low",
            reason=f"잉크가 {ink_ratio:.4%}뿐이라 글줄을 볼 수 없다 — 저장값을 무시하는 기존 동작 유지",
            line_scores=scores, ink_ratio=round(ink_ratio, 5),
            stored_rotation=page.rotation, unresolved="회전 전체",
        )

    if horizontal >= vertical * AXIS_MARGIN:
        return Orientation(
            rotation=0, axis="horizontal", confidence="high",
            reason=f"콘텐츠 스트림 그대로 그리면 글줄이 가로다 ({horizontal} vs {vertical})",
            line_scores=scores, ink_ratio=round(ink_ratio, 5),
            stored_rotation=page.rotation, unresolved="0°/180° (글줄의 위아래)",
        )

    if vertical >= horizontal * AXIS_MARGIN:
        # The page needs a quarter turn. Which of the two the pixels cannot say,
        # so the stored value breaks that tie — used only to pick a direction the
        # measurement already established was needed.
        quarter = page.rotation if page.rotation in (90, 270) else 90
        told = page.rotation in (90, 270)
        return Orientation(
            rotation=quarter,
            axis="vertical",
            confidence="high" if told else "low",
            reason=(f"글줄이 세로다 ({vertical} vs {horizontal}) — {quarter}° 회전. 방향은 "
                    + ("저장값(/Rotate)이 지정한 쪽" if told
                       else f"저장값 {page.rotation}°가 사분회전을 지정하지 않아 임의 선택")),
            line_scores=scores, ink_ratio=round(ink_ratio, 5),
            stored_rotation=page.rotation,
            unresolved=None if told else "사분회전 방향 (90°/270°)",
        )

    return Orientation(
        rotation=0, axis="undetermined", confidence="low",
        reason=f"두 축의 글줄 점수가 갈리지 않는다 ({horizontal} vs {vertical}) — 기존 동작 유지",
        line_scores=scores, ink_ratio=round(ink_ratio, 5),
        stored_rotation=page.rotation, unresolved="회전 전체",
    )


def render_upright_png(page: pymupdf.Page, dpi: int) -> tuple[bytes, Orientation]:
    """PNG of the page turned upright, with the orientation that produced it."""
    orientation = detect_orientation(page)
    with rotated(page, orientation.rotation):
        return page.get_pixmap(dpi=dpi).tobytes("png"), orientation
