"""Orientation detection on synthetic pages.

Every page here is built in the test: a paragraph of filler English, the same
paragraph authored sideways, and a page with next to no ink. No dataset page is
involved, so the cases stay readable and independent of the (uncommitted) input.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pymupdf
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from docsplit.ingest.render import detect_orientation, render_upright_png  # noqa: E402

FILLER = " ".join(["The quick brown fox jumps over the lazy dog."] * 60)


def _page(text: str, *, text_rotate: int = 0, stored_rotation: int = 0,
          fontsize: int = 10) -> pymupdf.Page:
    """One letter-size page of `text`, drawn at `text_rotate`, stored with `/Rotate`.

    The document is round-tripped through bytes so the rotation is read back from
    a real /Rotate entry rather than from an in-memory attribute.
    """
    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    box = pymupdf.Rect(60, 60, 552, 732)
    page.insert_textbox(box, text, fontsize=fontsize, rotate=text_rotate)
    page.set_rotation(stored_rotation)
    reopened = pymupdf.open("pdf", doc.tobytes())
    doc.close()
    return reopened[0]


def _page_of_png(png: bytes) -> pymupdf.Page:
    """The rendered image, back on a page — what the model is actually handed."""
    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    page.insert_image(page.rect, stream=png)
    return page


def test_upright_text_is_horizontal_and_needs_no_rotation():
    orientation = detect_orientation(_page(FILLER))
    assert orientation.axis == "horizontal"
    assert orientation.rotation == 0
    assert orientation.confidence == "high"
    assert orientation.line_scores["0/180"] > orientation.line_scores["90/270"]
    # The one thing the pixels cannot settle is reported, not guessed.
    assert orientation.unresolved == "0°/180° (글줄의 위아래)"


@pytest.mark.parametrize("text_rotate,stored", [(90, 270), (270, 90)])
def test_sideways_text_is_turned_by_the_stored_quarter(text_rotate: int, stored: int):
    """A PDF whose /Rotate is right: the page lies down unless the value is applied."""
    page = _page(FILLER, text_rotate=text_rotate, stored_rotation=stored)

    orientation = detect_orientation(page)
    assert orientation.axis == "vertical"
    assert orientation.rotation == stored
    assert orientation.confidence == "high"

    # And the image that comes out of it does stand upright.
    png, _ = render_upright_png(page, 72)
    assert detect_orientation(_page_of_png(png)).axis == "horizontal"


def test_sideways_text_without_a_stored_quarter_still_turns_but_says_so():
    orientation = detect_orientation(_page(FILLER, text_rotate=90, stored_rotation=0))
    assert orientation.axis == "vertical"
    assert orientation.rotation == 90  # arbitrary of the two, and flagged as such
    assert orientation.confidence == "low"
    assert orientation.unresolved == "사분회전 방향 (90°/270°)"


def test_near_blank_page_falls_back_to_the_previous_behaviour():
    orientation = detect_orientation(_page(".", fontsize=8, stored_rotation=90))
    assert orientation.axis == "undetermined"
    assert orientation.confidence == "low"
    assert orientation.rotation == 0  # /Rotate stays ignored, as before
    assert orientation.unresolved == "회전 전체"


def test_detection_leaves_the_stored_rotation_alone():
    """Later stages read page.rotation for geometry, so the probe must not keep it."""
    page = _page(FILLER, stored_rotation=180)
    detect_orientation(page)
    render_upright_png(page, 72)
    assert page.rotation == 180
