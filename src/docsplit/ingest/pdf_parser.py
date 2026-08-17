"""Native PDF text extraction using PyMuPDF.

First stage of the pipeline: per-page raw text plus cheap page metadata,
recorded as-is with no cleanup or quality fixes.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, asdict
from pathlib import Path

import pymupdf


@dataclass
class PageRecord:
    source_file: str
    page_index: int  # 0-based
    raw_text: str
    text_length: int  # len(raw_text)
    stripped_length: int  # len(raw_text.strip())
    is_empty: bool  # stripped_length == 0
    image_count: int
    width: float
    height: float
    rotation: int
    suspicious_char_ratio: float  # replacement/control/private-use chars over stripped_length

    def to_dict(self) -> dict:
        return asdict(self)


def _suspicious_char_ratio(text: str) -> float:
    stripped = text.strip()
    if not stripped:
        return 0.0
    suspicious = 0
    for ch in stripped:
        if ch == "�":
            suspicious += 1
            continue
        cat = unicodedata.category(ch)
        # Cc = control (whitespace already stripped out per-char below), Co = private use
        if cat in ("Cc", "Co") and ch not in ("\n", "\r", "\t"):
            suspicious += 1
    return suspicious / len(stripped)


def parse_pdf(pdf_path: Path) -> list[PageRecord]:
    """Extract native text and page metadata from every page of a PDF."""
    records: list[PageRecord] = []
    with pymupdf.open(pdf_path) as doc:
        for page in doc:
            raw_text = page.get_text("text")
            stripped_length = len(raw_text.strip())
            records.append(
                PageRecord(
                    source_file=pdf_path.name,
                    page_index=page.number,
                    raw_text=raw_text,
                    text_length=len(raw_text),
                    stripped_length=stripped_length,
                    is_empty=stripped_length == 0,
                    image_count=len(page.get_images(full=True)),
                    width=round(page.rect.width, 2),
                    height=round(page.rect.height, 2),
                    rotation=page.rotation,
                    suspicious_char_ratio=round(_suspicious_char_ratio(raw_text), 4),
                )
            )
    return records


def render_page_png(page: pymupdf.Page, dpi: int) -> bytes:
    """Render a page upright, ignoring its stored /Rotate value.

    PyMuPDF applies /Rotate when rasterizing, which is right when the value
    describes the content. In these scans it does not: the image was stored
    upright and /Rotate then turns it upside down or on its side, so the model
    is handed a page it has to read sideways. Rendering the content stream as
    authored gives an upright image for both the 90° and 180° cases.

    The rotation is restored afterwards because the same page object is reused
    for geometry-based extraction, which does depend on it.
    """
    original = page.rotation
    try:
        page.set_rotation(0)
        return page.get_pixmap(dpi=dpi).tobytes("png")
    finally:
        page.set_rotation(original)


def slugify(filename: str) -> str:
    """Filesystem-friendly stem for output paths ('INCOME - P & L_x.pdf' -> 'INCOME_P_L_x')."""
    stem = Path(filename).stem
    out = []
    prev_underscore = False
    for ch in stem:
        if ch.isalnum() or ch in ".-":
            out.append(ch)
            prev_underscore = False
        elif not prev_underscore:
            out.append("_")
            prev_underscore = True
    return "".join(out).strip("_")
