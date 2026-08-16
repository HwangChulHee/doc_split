"""Stages [3] and [4]: LLM grouping, then per-instance ordering.

Ordering (urla.md §6, credit_report.md §6-2):
  Path A (code): page markers form an intact 1..Y set (no dup/gap, Y = page
                 count) -> sort by marker.
  Path B (code): markers incomplete/absent -> policy fallback order. For URLA
                 that is the GSE section order (standard-backed); for CREDIT it
                 is the subtype order, which is observation-backed only and has
                 no standard guarantee (credit_report.md §8-3).
  Path C: no ordering signal at all -> order UNRESOLVED.
"""

from __future__ import annotations

import json
import re
from collections import Counter

from .cards import SignalCard
from .llm import LLMClient


# ── [3] grouping ──────────────────────────────────────────────
def group_pages(
    package: str,
    cards: list[SignalCard],
    raw_texts: dict[int, str],
    policy: dict,
    llm: LLMClient,
) -> dict:
    attached = {c.page: raw_texts[c.page] for c in cards if c.is_weak()}
    attached_str = (
        "\n\n".join(f"--- page {p} ---\n{t}" for p, t in sorted(attached.items()))
        if attached
        else "(없음)"
    )
    prompt_name = policy.get("prompts", {}).get("group", "group_urla")
    result = llm.complete_json(
        stage="grouping",
        prompt_name=prompt_name,
        variables={
            "expected_type": policy["type"],
            "cards_json": json.dumps([c.to_dict() for c in cards], ensure_ascii=False, indent=1),
            "attached_texts": attached_str,
        },
    )
    result["package"] = package

    known = {c.page for c in cards}
    assigned = [p for inst in result.get("instances", []) for p in inst.get("pages", [])]
    dup = [p for p, n in Counter(assigned).items() if n > 1]
    missing = sorted(known - set(assigned) - set(result.get("unresolved_pages", [])))
    unknown = sorted(set(assigned) - known)
    if dup or missing or unknown:
        result.setdefault("validation_warnings", []).append(
            {"duplicated": dup, "missing": missing, "unknown_pages": unknown}
        )
    return result


# ── [4] ordering ─────────────────────────────────────────────
def _try_marker_order(pages: list[int], cards_by_page: dict[int, SignalCard]) -> list[int] | None:
    """Path A: single consistent denominator, bijective 1..Y == page count."""
    y_values = [m["y"] for p in pages for m in cards_by_page[p].page_marker_candidates]
    if not y_values:
        return None
    y = Counter(y_values).most_common(1)[0][0]
    if y != len(pages):
        return None
    assignment: dict[int, int] = {}
    for p in pages:
        ns = {m["n"] for m in cards_by_page[p].page_marker_candidates if m["y"] == y}
        if len(ns) != 1:
            return None
        assignment[p] = ns.pop()
    if sorted(assignment.values()) != list(range(1, y + 1)):
        return None
    return sorted(pages, key=lambda p: assignment[p])


def _fallback_rank(card: SignalCard, policy: dict) -> tuple | None:
    """Path B rank: (subtype order, section/L number). None = no signal at all."""
    ordering = policy.get("ordering", {})
    order = ordering.get("subtype_order", [])
    nums: list[int] = []
    for pattern_key in ("section_rank_pattern", "l_rank_pattern"):
        pattern = ordering.get(pattern_key)
        if not pattern:
            continue
        pat = re.compile(pattern)
        for title in card.sections_found:
            m = pat.search(title.lower())
            if m:
                nums.append(int(m.group(1)))
    if card.subtype is None and not nums:
        return None
    sub_rank = order.index(card.subtype) if card.subtype in order else len(order)
    return (sub_rank, min(nums) if nums else 99)


def order_instances(grouping: dict, cards: list[SignalCard], policy: dict) -> dict:
    cards_by_page = {c.page: c for c in cards}
    fallback_note = policy.get("ordering", {}).get(
        "fallback_evidence", "표준 섹션 순서로 정렬"
    )
    out = {"package": grouping.get("package"), "instances": []}
    for inst in grouping.get("instances", []):
        pages = [p for p in inst.get("pages", []) if p in cards_by_page]
        entry = {"instance_id": inst.get("instance_id"), "unresolved": []}

        ordered = _try_marker_order(pages, cards_by_page)
        if ordered is not None:
            entry["ordered_pages"] = ordered
            entry["method"] = "CODE_A_PAGE_MARKER"
            entry["evidence"] = f"page_marker 무결(1..{len(pages)}, 겹침·공백 없음)로 코드 정렬"
        else:
            ranked, unresolved = [], []
            for p in pages:
                r = _fallback_rank(cards_by_page[p], policy)
                if r is None:
                    unresolved.append(p)
                else:
                    ranked.append((r, p))
            ranked.sort()
            entry["ordered_pages"] = [p for _, p in ranked]
            entry["unresolved"] = unresolved
            entry["method"] = "CODE_B_FALLBACK_ORDER"
            entry["evidence"] = (
                f"page_marker 불완전 → {fallback_note}"
                + (f"; 순서 신호 없는 {len(unresolved)}페이지는 UNRESOLVED" if unresolved else "")
            )
        out["instances"].append(entry)
    return out
