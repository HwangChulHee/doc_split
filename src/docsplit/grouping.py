"""Stages [3] and [4]: LLM grouping, then per-instance ordering.

Ordering (docs/classification/urla.md §6):
  Path A (code): page markers form an intact 1..Y set (no dup/gap, Y = page
                 count) -> sort by marker.
  Path B: markers incomplete/absent -> standard section order from the policy
          (subtype order, then section/L number). Pages without any section
          signal fall through to
  Path C: order UNRESOLVED.
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
    result = llm.complete_json(
        stage="grouping",
        prompt_name="group_urla",
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
    y_values = [
        m["y"]
        for p in pages
        for m in cards_by_page[p].page_marker_candidates
    ]
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


def _section_rank(card: SignalCard, policy: dict) -> tuple | None:
    """Path B rank: (subtype order, section/L number). None = no signal."""
    order = policy["ordering"]["subtype_order"]
    sec_pat = re.compile(policy["ordering"]["section_rank_pattern"])
    l_pat = re.compile(policy["ordering"]["l_rank_pattern"])
    nums = []
    for title in card.sections_found:
        t = title.lower()
        m = sec_pat.search(t) or l_pat.search(t)
        if m:
            nums.append(int(m.group(1)))
    if card.subtype is None and not nums:
        return None
    sub_rank = order.index(card.subtype) if card.subtype in order else len(order)
    return (sub_rank, min(nums) if nums else 99)


def order_instances(grouping: dict, cards: list[SignalCard], policy: dict) -> dict:
    cards_by_page = {c.page: c for c in cards}
    out = {"package": grouping.get("package"), "instances": []}
    for inst in grouping.get("instances", []):
        pages = list(inst.get("pages", []))
        entry = {"instance_id": inst.get("instance_id"), "unresolved": []}

        ordered = _try_marker_order(pages, cards_by_page)
        if ordered is not None:
            entry["ordered_pages"] = ordered
            entry["method"] = "CODE_A_PAGE_MARKER"
            entry["evidence"] = (
                f"page_marker 무결(1..{len(pages)}, 겹침·공백 없음)로 코드 정렬"
            )
        else:
            ranked, unresolved = [], []
            for p in pages:
                r = _section_rank(cards_by_page[p], policy)
                (ranked if r is not None else unresolved).append((r, p) if r is not None else p)
            ranked.sort()
            entry["ordered_pages"] = [p for _, p in ranked]
            entry["unresolved"] = unresolved
            entry["method"] = "CODE_B_SECTION_ORDER"
            entry["evidence"] = (
                "page_marker 불완전 → 표준 섹션 순서(Section 1→9 → 부속 → L1→L4)로 정렬"
                + (f"; 섹션 신호 없는 {len(unresolved)}페이지는 UNRESOLVED" if unresolved else "")
            )
        out["instances"].append(entry)
    return out
