"""Stage [1]: page-level type judgment by combining policy signals.

Combination rule (docs/classification/urla.md §3-3, thresholds live in the
policy file and are not tuning knobs):

    D >= decisive_min                    -> RULE_HIGH
    distinct S >= supportive_min         -> RULE_MEDIUM
    distinct S == 1                      -> DEFER_LLM
    no signal                            -> NO_SIGNAL
    empty text                           -> DEFER_VLM
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict

from .normalize import PageText
from .signals import SignalResult, detect_subtype, evaluate_signals


@dataclass
class PageClassification:
    package: str
    page: int
    type: str | None
    grade: str  # RULE_HIGH | RULE_MEDIUM | DEFER_LLM | NO_SIGNAL | DEFER_VLM | LLM | LLM_UNRESOLVED
    subtype: str | None = None
    signals: dict = field(default_factory=dict)
    matches: list = field(default_factory=list)
    flags: dict = field(default_factory=dict)
    llm: dict | None = None  # filled when a DEFER_LLM page is resolved by the LLM

    def to_dict(self) -> dict:
        return asdict(self)


def classify_page(package: str, page_index: int, raw_text: str, policy: dict) -> tuple[PageClassification, SignalResult, PageText]:
    page = PageText.from_raw(raw_text)
    type_name = policy["type"]

    if not page.fulltext:
        cls = PageClassification(package, page_index, None, "DEFER_VLM")
        return cls, SignalResult(), page

    res = evaluate_signals(page, policy)

    if res.excluded_as:
        cls = PageClassification(
            package, page_index, None, "NO_SIGNAL",
            flags={"excluded_as": res.excluded_as},
        )
        return cls, res, page

    combine = policy["combine"]
    d_ids, s_ids = res.decisive_ids(), res.supportive_ids()
    matches = [
        {"id": h.signal_id, "kind": h.kind, "method": h.method, "text": h.matched_text}
        for h in res.decisive + res.supportive
    ]

    if len(d_ids) >= combine["decisive_min"]:
        grade, ptype = "RULE_HIGH", type_name
    elif len(s_ids) >= combine["supportive_min"]:
        grade, ptype = "RULE_MEDIUM", type_name
    elif len(s_ids) == 1:
        grade, ptype = "DEFER_LLM", None
    else:
        grade, ptype = "NO_SIGNAL", None

    subtype, conflict = (None, False)
    if ptype is not None:
        subtype, conflict = detect_subtype(page, res, policy)

    cls = PageClassification(
        package, page_index, ptype, grade,
        subtype=subtype,
        signals={"decisive": d_ids, "supportive": s_ids},
        matches=matches,
        flags={"subtype_conflict": conflict} if conflict else {},
    )
    return cls, res, page
