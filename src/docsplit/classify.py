"""Stage [1]: page-level type judgment by combining policy signals.

Combination rule (docs/classification/urla.md §3-3, credit_report.md §4-1 —
thresholds live in the policy file and are not tuning knobs)::

    decisive >= decisive_min                     -> RULE_HIGH
    distinct supportive >= supportive_min        -> RULE_MEDIUM
    distinct supportive == 1                     -> DEFER_LLM
    no signal                                    -> NO_SIGNAL
    empty text                                   -> DEFER_VLM
    adjacent-document phrase matched             -> EXCLUDED_ADJACENT

Vendor decisive signals require that vendor's identity; the demotion happens in
signals.evaluate_signals, so the arithmetic here stays uniform across types.

Type competition (credit_report.md §4-2): every available policy is evaluated
independently. When two or more types reach RULE_HIGH the page is flagged and
handed to the LLM rather than resolved by an arbitrary precedence order.
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
    grade: str
    subtype: str | None = None
    signals: dict = field(default_factory=dict)
    matches: list = field(default_factory=list)
    flags: dict = field(default_factory=dict)
    llm: dict | None = None  # filled when a deferred page is resolved by the LLM

    def to_dict(self) -> dict:
        return asdict(self)


def grade_for(res: SignalResult, policy: dict) -> tuple[str, str | None]:
    """Apply the combination rule. Returns (grade, type or None)."""
    combine = policy["combine"]
    if len(res.decisive_ids()) >= combine["decisive_min"]:
        return "RULE_HIGH", policy["type"]
    if len(res.supportive_ids()) >= combine["supportive_min"]:
        return "RULE_MEDIUM", policy["type"]
    if len(res.supportive_ids()) == 1:
        return "DEFER_LLM", None
    return "NO_SIGNAL", None


def classify_page(
    package: str,
    page_index: int,
    raw_text: str,
    policy: dict,
    competing_policies: list[dict] | None = None,
) -> tuple[PageClassification, SignalResult, PageText]:
    page = PageText.from_raw(raw_text)

    if not page.fulltext:
        return PageClassification(package, page_index, None, "DEFER_VLM"), SignalResult(), page

    res = evaluate_signals(page, policy)

    if res.excluded_as:
        cls = PageClassification(
            package, page_index, None, "EXCLUDED_ADJACENT",
            flags={"excluded_as": res.excluded_as},
        )
        return cls, res, page

    grade, ptype = grade_for(res, policy)
    flags: dict = {}

    # Type competition: only a rival that also reaches RULE_HIGH creates a conflict.
    if grade == "RULE_HIGH":
        rivals = []
        for other in competing_policies or []:
            if other["type"] == policy["type"]:
                continue
            other_res = evaluate_signals(page, other)
            if other_res.excluded_as:
                continue
            if grade_for(other_res, other)[0] == "RULE_HIGH":
                rivals.append(other["type"])
        if rivals:
            flags["type_conflict"] = sorted([policy["type"], *rivals])
            grade, ptype = "DEFER_LLM", None

    subtype, conflict = (None, False)
    if ptype is not None:
        subtype, conflict = detect_subtype(page, res, policy)
        if conflict:
            flags["subtype_conflict"] = True

    cls = PageClassification(
        package, page_index, ptype, grade,
        subtype=subtype,
        signals={
            "decisive": res.decisive_ids(),
            "supportive": res.supportive_ids(),
            "identities": res.identities,
            "layers": res.layers(),
        },
        matches=[h.to_dict() for h in res.all_hits()],
        flags=flags,
    )
    return cls, res, page
