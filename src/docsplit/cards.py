"""Stage [2]: signal-card extraction for grouping.

Philosophy (docs/classification/urla.md §4, credit_report.md §5): the extractor
collects candidates, including false positives — judgment belongs to stage [3].
If a renderer changes and signals stop matching, cards get thin and stage [3]
falls back to raw text on its own.

Everything extracted here is policy-driven (``cards:`` section):

======================  =======================================================
``id_patterns``         {field name: regex} over normalized page text
``date_patterns``       regexes collected into ``date_candidates``
``page_marker_pattern``  ``N of Y`` variants (body false positives kept)
``name_anchor``         label text; values are read from the same visual line
``printed_codes``       literal lines to record (material, never a rule)
``signal_phrase_fields``  signal IDs whose matched phrases go to sections_found
``id_block_signal``     signal ID that marks a trusted identification block
======================  =======================================================
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
    vendor_identity: list[str] = field(default_factory=list)
    name_candidates: list[str] = field(default_factory=list)
    id_candidates: dict = field(default_factory=dict)
    date_candidates: list[str] = field(default_factory=list)
    page_marker_candidates: list[dict] = field(default_factory=list)
    sections_found: list[str] = field(default_factory=list)
    printed_codes: list[str] = field(default_factory=list)
    id_block_present: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    def is_weak(self) -> bool:
        """No names, no ids, no markers — grouping gets this page's raw text."""
        return not (
            self.name_candidates
            or any(self.id_candidates.values())
            or self.page_marker_candidates
        )


def _names_from_widgets(pdf_page: pymupdf.Page) -> list[str]:
    out = []
    for w in pdf_page.widgets() or []:
        fname = (w.field_name or "").lower()
        if ("name" in fname or "borrower" in fname) and (w.field_value or "").strip():
            out.append(w.field_value.strip())
    return out


def _names_from_anchor(pdf_page: pymupdf.Page, cfg: dict, exclude: set[str]) -> list[str]:
    """Values sitting on the same visual line as the label, to its right.

    Text order in the extracted layer does not follow the visual layout, so
    "the line after the label" is not reliable — geometry is.
    """
    anchor = normalize(cfg["name_anchor"])
    window = cfg.get("name_window_pt", {"y": 5, "x": 320})
    wy, wx = window["y"], window["x"]
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
    cfg = policy.get("cards", {})
    card = SignalCard(package=package, page=page_index, subtype=subtype)
    card.vendor_identity = list(signal_result.identities)

    codes = {normalize(c) for c in cfg.get("printed_codes", [])}
    if pdf_page is not None and cfg.get("name_anchor"):
        card.name_candidates = _names_from_widgets(pdf_page)
        if not card.name_candidates:
            card.name_candidates = _names_from_anchor(pdf_page, cfg, exclude=codes)

    for fieldname, pattern in (cfg.get("id_patterns") or {}).items():
        values = sorted(set(re.findall(pattern, page.fulltext)))
        if fieldname == "uli":  # digit-only strings are loan numbers, not ULIs
            values = [v for v in values if not v.isdigit()]
        card.id_candidates[fieldname] = values

    dates: list[str] = []
    for pattern in cfg.get("date_patterns", []):
        dates += re.findall(pattern, page.fulltext)
    card.date_candidates = sorted(set(dates))

    if cfg.get("page_marker_pattern"):
        for m in re.finditer(cfg["page_marker_pattern"], page.fulltext):
            card.page_marker_candidates.append(
                {"n": int(m.group(1)), "y": int(m.group(2)), "raw": m.group(0)}
            )

    card.sections_found = sorted(
        {
            p
            for sid in cfg.get("signal_phrase_fields", [])
            for p in signal_result.titles_matched.get(sid, [])
        }
    )
    card.printed_codes = [c for c in cfg.get("printed_codes", []) if normalize(c) in page.lines]
    id_block_signal = cfg.get("id_block_signal")
    card.id_block_present = bool(id_block_signal) and any(
        h.signal_id == id_block_signal for h in signal_result.all_hits()
    )
    return card
