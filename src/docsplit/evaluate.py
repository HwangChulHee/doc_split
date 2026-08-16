"""V1–V4 verification against the ground truth (docs/classification/urla.md §7).

GT is for verification only — no threshold tuning happens here. On failure the
report records details (page, signals, suspected cause) and policy changes are
left to the user.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

# 정답 없는 두 번째 패키지의 URLA 기대 페이지 (관찰 결과 기준)
EXPECTED_SECONDARY_URLA_PAGES = {"02": [12, 15, 17, 19, 22, 24, 28, 34, 36, 42]}


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str
    failures: list[dict] = field(default_factory=list)


def _cls_by_page(classifications: list[dict], package: str) -> dict[int, dict]:
    return {c["page"]: c for c in classifications if c["package"] == package}


def run_verifications(
    classifications: list[dict],
    grouping: dict | None,
    ordering: dict | None,
    gt_rows: list[dict],
    gt_label: str = "01",
    secondary_label: str = "02",
) -> list[CheckResult]:
    p01 = _cls_by_page(classifications, gt_label)
    p02 = _cls_by_page(classifications, secondary_label)
    expected_secondary = EXPECTED_SECONDARY_URLA_PAGES.get(secondary_label, [])
    gt_urla = sorted(r["input_page"] for r in gt_rows if r["document_type"] == "URLA_1003")
    gt_by_page = {r["input_page"]: r for r in gt_rows}

    results = []

    # V1: 모든 URLA 페이지가 RULE_HIGH/MEDIUM 도달
    v1_fail = []
    targets = [(gt_label, p, p01.get(p)) for p in gt_urla] + [
        (secondary_label, p, p02.get(p)) for p in expected_secondary
    ]
    for pkg, page, c in targets:
        grade = c["grade"] if c else "MISSING"
        if grade not in ("RULE_HIGH", "RULE_MEDIUM"):
            v1_fail.append({"package": pkg, "page": page, "grade": grade, "signals": c and c["signals"]})
    results.append(
        CheckResult(
            "V1", not v1_fail,
            f"URLA {len(targets)}p 중 {len(targets) - len(v1_fail)}p RULE_HIGH/MEDIUM 도달",
            v1_fail,
        )
    )

    # V2: 비-URLA 페이지에서 decisive 오발 0
    v2_fail = []
    non_urla = [(gt_label, p, c) for p, c in p01.items() if p not in set(gt_urla)] + [
        (secondary_label, p, c) for p, c in p02.items() if p not in set(expected_secondary)
    ]
    for pkg, page, c in non_urla:
        if c["signals"] and c["signals"].get("decisive"):
            v2_fail.append({"package": pkg, "page": page, "decisive": c["signals"]["decisive"], "matches": c["matches"]})
    results.append(
        CheckResult("V2", not v2_fail, f"비-URLA {len(non_urla)}p에서 D 신호 오발 {len(v2_fail)}건", v2_fail)
    )

    # V3: 비-URLA 페이지에서 서로 다른 S ≥ 2 동시 성립 0
    v3_fail = []
    for pkg, page, c in non_urla:
        s = c["signals"].get("supportive", []) if c["signals"] else []
        if len(s) >= 2:
            v3_fail.append({"package": pkg, "page": page, "supportive": s})
    results.append(
        CheckResult("V3", not v3_fail, f"비-URLA {len(non_urla)}p에서 S≥2 동시 성립 {len(v3_fail)}건", v3_fail)
    )

    # V4: GT 패키지의 URLA가 1 instance + 순서가 GT source_page와 일치
    if grouping is None or ordering is None:
        results.append(CheckResult("V4", False, "SKIPPED (--no-llm — 그룹핑 미수행)", []))
        return results

    v4_fail = []
    instances = grouping.get("instances", [])
    if len(instances) != 1:
        v4_fail.append({"reason": f"instance 수 {len(instances)} (기대 1)", "instances": [i.get("pages") for i in instances]})
    else:
        got = sorted(instances[0].get("pages", []))
        if got != gt_urla:
            v4_fail.append({"reason": "instance 페이지 집합 불일치", "got": got, "expected": gt_urla})
    if grouping.get("unresolved_pages"):
        v4_fail.append({"reason": "unresolved_pages 존재", "pages": grouping["unresolved_pages"]})

    if not v4_fail:
        ordered = ordering["instances"][0].get("ordered_pages", [])
        seq = [gt_by_page[p]["source_page"] for p in ordered]
        if seq != list(range(len(ordered))):
            v4_fail.append({"reason": "순서 불일치", "ordered_input_pages": ordered, "gt_source_pages": seq})
    results.append(
        CheckResult("V4", not v4_fail, "GT 패키지 URLA 1 instance·GT 순서 일치" if not v4_fail else "그룹핑/순서 불일치", v4_fail)
    )
    return results


def render_report(
    results: list[CheckResult],
    grouping: dict | None,
    ordering: dict | None,
    usage: dict | None,
    no_llm: bool,
) -> str:
    lines = ["# URLA 파이프라인 리포트", ""]
    lines += ["## 검증 결과 (V1–V4)", "", "| # | 기준 | 결과 | 상세 |", "|---|---|---|---|"]
    for r in results:
        lines.append(f"| {r.name} | {r.detail} | {'✅ PASS' if r.passed else '❌ FAIL'} | {len(r.failures)}건 |")
    lines.append("")
    for r in results:
        if r.failures:
            lines += [f"### {r.name} 실패 상세", "", "```json",
                      json.dumps(r.failures, ensure_ascii=False, indent=2), "```", ""]

    lines.append("## 그룹핑 결과")
    lines.append("")
    if no_llm or grouping is None:
        lines.append("SKIPPED (--no-llm)")
    else:
        lines += ["```json", json.dumps(grouping, ensure_ascii=False, indent=2), "```"]
    lines.append("")
    lines.append("## 순서 정렬 결과")
    lines.append("")
    if no_llm or ordering is None:
        lines.append("SKIPPED (--no-llm)")
    else:
        lines += ["```json", json.dumps(ordering, ensure_ascii=False, indent=2), "```"]
    lines.append("")
    lines.append("## LLM 사용량")
    lines.append("")
    if usage:
        lines += ["```json", json.dumps(usage, ensure_ascii=False, indent=2), "```"]
    else:
        lines.append("호출 없음")
    lines.append("")
    return "\n".join(lines)
