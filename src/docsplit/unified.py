"""Unified classification: every policy scores every page, once.

The per-type pipelines each re-sent their unclaimed pages to the LLM with only
their own type as a candidate, so one page could be asked about four times and
still never be offered the type it actually was. Here the page is scored by all
policies first and asked about at most once, with every type on the table.

Decision order (income_doc handoff §2) — grades are comparable because a
decisive signal means something stronger than a supportive pair:

    no text                       -> DEFER_VLM   (image path)
    exactly one RULE_HIGH         -> that type, by rule
    two or more RULE_HIGH         -> TYPE_CONFLICT -> LLM
    no HIGH, exactly one MEDIUM   -> that type, by rule
    no HIGH, several MEDIUM       -> TYPE_CONFLICT -> LLM
    anything else                 -> DEFER_LLM  (all five types offered)

``OTHER`` has no policy file: it is what the LLM answers when a page belongs to
none of the four, which is why it can only be reached on the LLM path.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict

from .classify import grade_for
from .normalize import PageText
from .signals import detect_subtype, evaluate_signals

OTHER_TYPE = "OTHER"
RULE_GRADES = ("RULE_HIGH", "RULE_MEDIUM")


@dataclass
class TypeScore:
    grade: str
    decisive: list[str] = field(default_factory=list)
    supportive: list[str] = field(default_factory=list)
    identities: list[str] = field(default_factory=list)
    excluded_as: str | None = None


@dataclass
class PageVerdict:
    package: str
    page: int
    type: str | None
    subtype: str | None
    grade: str  # final grade, after LLM/VLM
    rule_grade: str  # what the rules alone said
    decided_by: str  # rule | llm | vlm | deferred
    scores: dict[str, dict] = field(default_factory=dict)
    flags: dict = field(default_factory=dict)
    llm: dict | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def score_page(page: PageText, policies: dict[str, dict]) -> dict[str, TypeScore]:
    """Grade one page against every policy, keeping each policy's evidence."""
    scores: dict[str, TypeScore] = {}
    for type_name, policy in policies.items():
        res = evaluate_signals(page, policy)
        if res.excluded_as:
            scores[type_name] = TypeScore("EXCLUDED_ADJACENT", excluded_as=res.excluded_as)
            continue
        scores[type_name] = TypeScore(
            grade=grade_for(res, policy)[0],
            decisive=res.decisive_ids(),
            supportive=res.supportive_ids(),
            identities=list(res.identities),
        )
    return scores


def decide(scores: dict[str, TypeScore], has_text: bool) -> tuple[str | None, str, dict]:
    """Apply the decision order. Returns (type or None, grade, flags)."""
    if not has_text:
        return None, "DEFER_VLM", {}

    highs = sorted(t for t, s in scores.items() if s.grade == "RULE_HIGH")
    if len(highs) == 1:
        return highs[0], "RULE_HIGH", {}
    if len(highs) > 1:
        return None, "DEFER_LLM", {"type_conflict": highs}

    mediums = sorted(t for t, s in scores.items() if s.grade == "RULE_MEDIUM")
    if len(mediums) == 1:
        return mediums[0], "RULE_MEDIUM", {}
    if len(mediums) > 1:
        return None, "DEFER_LLM", {"type_conflict": mediums}

    return None, "DEFER_LLM", {}


def classify_page_unified(
    package: str, page_index: int, raw_text: str, policies: dict[str, dict]
) -> tuple[PageVerdict, PageText, dict]:
    """Rule-only verdict for one page, plus the per-policy signal results."""
    page = PageText.from_raw(raw_text)
    scores = score_page(page, policies) if page.fulltext else {}
    ptype, grade, flags = decide(scores, bool(page.fulltext))

    subtype = None
    if ptype is not None:
        res = evaluate_signals(page, policies[ptype])
        subtype, conflict = detect_subtype(page, res, policies[ptype])
        if conflict:
            flags["subtype_conflict"] = True

    verdict = PageVerdict(
        package=package,
        page=page_index,
        type=ptype,
        subtype=subtype,
        grade=grade,
        rule_grade=grade,
        decided_by="rule" if ptype is not None else "deferred",
        scores={t: asdict(s) for t, s in sorted(scores.items())},
        flags=flags,
    )
    return verdict, page, {t: s for t, s in scores.items()}


def llm_variables(verdict: PageVerdict, page_text: str, subtype_options: list[str]) -> dict:
    """Prompt inputs for a page the rules could not settle.

    The rule evidence for *every* type goes in, so the model is choosing with
    the same information the rules had rather than guessing blind.
    """
    conflict = verdict.flags.get("type_conflict")
    summary = {
        t: {k: v for k, v in s.items() if v and k != "excluded_as"}
        for t, s in verdict.scores.items()
        if s.get("grade") != "NO_SIGNAL"
    }
    return {
        "candidate_types": ", ".join(conflict or [*sorted(verdict.scores), OTHER_TYPE]),
        "reason": "TYPE_CONFLICT" if conflict else verdict.rule_grade,
        "signal_summary": json.dumps(summary or {"note": "규칙 신호 없음"}, ensure_ascii=False),
        "subtype_options": ", ".join(subtype_options) or "(없음)",
        "page_text": page_text,
    }


def apply_llm_answer(verdict: PageVerdict, parsed: dict, known_types: set[str]) -> None:
    """Fold an LLM/VLM answer into the verdict."""
    verdict.llm = parsed
    answer = parsed.get("type")
    if answer in known_types or answer == OTHER_TYPE:
        verdict.type = answer
        verdict.subtype = verdict.subtype or parsed.get("subtype")
        verdict.grade = "VLM" if verdict.rule_grade == "DEFER_VLM" else "LLM"
        verdict.decided_by = "vlm" if verdict.rule_grade == "DEFER_VLM" else "llm"
    else:
        verdict.grade = "UNRESOLVED"
        verdict.decided_by = "deferred"
