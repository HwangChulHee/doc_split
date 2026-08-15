"""Stage [2]: signal-card extraction for grouping.

Philosophy (docs/classification/urla.md §4): the extractor collects
candidates, including false positives — judgment belongs to stage [3].

Extraction paths per field:
  name_candidates   AcroForm widgets first; fallback to label-anchor geometry
                    (same visual line, right of the label, narrow window)
  id_candidates     regex over normalized text; "trusted" flag when the page
                    carries the top identification block (S2)
  page_markers      regex incl. body false positives, collected as-is
  sections_found    reuse of stage-[1] S3/S4 matches (no extra scan)
  printed_codes     literal line presence (material, not a rule)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict

import pymupdf

from .normalize import PageText, normalize
from .signals import SignalResult


@dataclass
class SignalCard:
    package: str
    page: int
    subtype: str | None
    name_candidates: list[str] = field(default_factory=list)
    id_candidates: dict = field(default_factory=dict)
    page_marker_candidates: list[dict] = field(default_factory=list)
    sections_found: list[str] = field(default_factory=list)
    printed_codes: list[str] = field(default_factory=list)
    id_block_present: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    def is_weak(self) -> bool:
        """No names, no ids, no markers — grouping gets raw text attached."""
        return not (self.name_candidates or any(self.id_candidates.values()) or self.page_marker_candidates)


def _names_from_widgets(pdf_page: pymupdf.Page) -> list[str]:
    out = []
    for w in pdf_page.widgets() or []:
        fname = (w.field_name or "").lower()
        if ("name" in fname or "borrower" in fname) and (w.field_value or "").strip():
            out.append(w.field_value.strip())
    return out


def _names_from_anchor(pdf_page: pymupdf.Page, cfg: dict, exclude: set[str]) -> list[str]:
    anchor = normalize(cfg["name_anchor"])
    wy, wx = cfg["name_window_pt"]["y"], cfg["name_window_pt"]["x"]
    out: list[str] = []
    d = pdf_page.get_text("dict")
    lines = [
        (ln["bbox"], "".join(s["text"] for s in ln["spans"]).strip())
        for blk in d["blocks"]
        for ln in blk.get("lines", [])
    ]
    for bbox, txt in lines:
        if anchor not in normalize(txt):
            continue
        rest = txt.split(":", 1)[1].strip() if ":" in txt else ""
        if rest:
            out.append(rest)
        for obox, otxt in lines:
            if (
                otxt
                and abs(obox[1] - bbox[1]) <= wy
                and bbox[2] - 2 <= obox[0] <= bbox[2] + wx
                and normalize(otxt) not in exclude
                and anchor not in normalize(otxt)
            ):
                out.append(otxt)
    seen, dedup = set(), []
    for n in out:
        if n not in seen:
            seen.add(n)
            dedup.append(n)
    return dedup


def build_card(
    package: str,
    page_index: int,
    page: PageText,
    signal_result: SignalResult,
    subtype: str | None,
    policy: dict,
    pdf_page: pymupdf.Page | None,
) -> SignalCard:
    cfg = policy["cards"]
    card = SignalCard(package=package, page=page_index, subtype=subtype)

    marker_pat = re.compile(cfg["page_marker_pattern"])
    codes = {normalize(c) for c in cfg["printed_codes"]}

    if pdf_page is not None:
        card.name_candidates = _names_from_widgets(pdf_page)
        if not card.name_candidates:
            card.name_candidates = _names_from_anchor(pdf_page, cfg, exclude=codes)

    loans = sorted(set(re.findall(cfg["loan_number_pattern"], page.fulltext)))
    ulis = sorted(set(re.findall(cfg["uli_pattern"], page.fulltext)))
    card.id_candidates = {"loan_number": loans, "uli": [u for u in ulis if not u.isdigit()]}
    card.id_block_present = any(h.signal_id == "S2" for h in signal_result.supportive)

    for m in marker_pat.finditer(page.fulltext):
        card.page_marker_candidates.append(
            {"n": int(m.group(1)), "y": int(m.group(2)), "raw": m.group(0)}
        )

    card.sections_found = sorted(
        {p for sid in ("S3", "S4") for p in signal_result.titles_matched.get(sid, [])}
    )
    card.printed_codes = [c for c in cfg["printed_codes"] if normalize(c) in page.lines]
    return card
