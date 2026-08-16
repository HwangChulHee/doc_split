"""Verification against the ground truth (urla.md §7, credit_report.md §7).

GT is for verification only — **no threshold tuning happens here**. On failure
the report records details (page, signals, suspected cause) and any policy
change is left to the user.

Checks, named ``<prefix>V1``..``V4`` (URLA has no prefix, CREDIT uses ``C-``):

  V1  every expected page of the type reaches RULE_HIGH/RULE_MEDIUM
  V2  no decisive signal fires on a page of another type
  V3  no two distinct supportive IDs fire together on a page of another type
  V4  the first package's pages form one instance ordered as the GT says

CREDIT adds C-V5, which is a **measurement, not a pass/fail check**: how many
pages the universal (vendor-independent) signals alone would reach.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "expected_pages.yaml"


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str
    failures: list[dict] = field(default_factory=list)
    measurement: dict | None = None  # set for measure-only items (C-V5)


def load_expected_pages(type_name: str, known_labels: list[str]) -> tuple[dict, list[str]]:
    """Return ({label: {expected, undecided}}, warnings).

    A configured label that does not exist in the data is a warning, not a
    silent empty list — otherwise V2/V3 would quietly treat every page of that
    package as a counter-example.
    """
    warnings: list[str] = []
    if not CONFIG_PATH.exists():
        return {}, [f"{CONFIG_PATH} 없음 — 두 번째 패키지 기대 페이지 검증을 건너뜁니다."]
    cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    per_type = cfg.get(type_name) or {}
    out = {}
    for label, entry in per_type.items():
        if label not in known_labels:
            warnings.append(
                f"config/expected_pages.yaml 의 {type_name}.{label} 라벨이 실제 패키지"
                f"({', '.join(known_labels)})에 없습니다 — 해당 기대값은 검증에 쓰이지 않습니다."
            )
            continue
        out[label] = {
            "expected": list(entry.get("expected", [])),
            "undecided": list(entry.get("undecided", [])),
        }
    for label in known_labels[1:]:
        if label not in per_type:
            warnings.append(
                f"패키지 {label} 의 {type_name} 기대 페이지가 config에 없습니다 — "
                "V1은 이 패키지를 건너뛰고 V2/V3는 전 페이지를 반례로 취급합니다."
            )
    return out, warnings


def _by_page(classifications: list[dict], package: str) -> dict[int, dict]:
    return {c["page"]: c for c in classifications if c["package"] == package}


def run_verifications(
    type_name: str,
    classifications: list[dict],
    grouping: dict | None,
    ordering: dict | None,
    gt_rows: list[dict],
    gt_label: str,
    expected_pages: dict,
    prefix: str = "",
    universal_only: dict | None = None,
) -> list[CheckResult]:
    gt_pages = sorted(r["input_page"] for r in gt_rows if r["document_type"] == type_name)
    gt_by_page = {r["input_page"]: r for r in gt_rows}
    primary = _by_page(classifications, gt_label)

    def name(n: int) -> str:
        return f"{prefix}V{n}"

    results: list[CheckResult] = []

    # ── V1: expected pages reach a rule grade ────────────────
    targets = [(gt_label, p, primary.get(p)) for p in gt_pages]
    for label, entry in expected_pages.items():
        pages = _by_page(classifications, label)
        targets += [(label, p, pages.get(p)) for p in entry["expected"]]
    v1_fail = []
    for label, page, c in targets:
        grade = c["grade"] if c else "MISSING"
        if grade not in ("RULE_HIGH", "RULE_MEDIUM"):
            v1_fail.append(
                {"package": label, "page": page, "grade": grade,
                 "signals": c and c.get("signals"), "matches": c and c.get("matches")}
            )
    per_pkg = {}
    for label, page, c in targets:
        tot, ok = per_pkg.get(label, (0, 0))
        reached = bool(c) and c["grade"] in ("RULE_HIGH", "RULE_MEDIUM")
        per_pkg[label] = (tot + 1, ok + (1 if reached else 0))
    breakdown = ", ".join(f"pkg{lb} {ok}/{tot}" for lb, (tot, ok) in sorted(per_pkg.items()))
    results.append(
        CheckResult(
            name(1), not v1_fail,
            f"{type_name} 기대 {len(targets)}p 중 {len(targets) - len(v1_fail)}p "
            f"RULE_HIGH/MEDIUM 도달 ({breakdown})",
            v1_fail,
        )
    )

    # ── counter-examples: pages of another type ──────────────
    others: list[tuple[str, int, dict]] = [
        (gt_label, p, c) for p, c in primary.items() if p not in set(gt_pages)
    ]
    for label, entry in expected_pages.items():
        skip = set(entry["expected"]) | set(entry["undecided"])
        others += [(label, p, c) for p, c in _by_page(classifications, label).items() if p not in skip]

    v2_fail = [
        {"package": lb, "page": p, "decisive": c["signals"]["decisive"], "matches": c["matches"]}
        for lb, p, c in others
        if c.get("signals", {}).get("decisive")
    ]
    results.append(
        CheckResult(name(2), not v2_fail,
                    f"비-{type_name} {len(others)}p 에서 결정적 신호 오발 {len(v2_fail)}건", v2_fail)
    )

    v3_fail = [
        {"package": lb, "page": p, "supportive": c["signals"]["supportive"], "matches": c["matches"]}
        for lb, p, c in others
        if len(c.get("signals", {}).get("supportive", [])) >= 2
    ]
    results.append(
        CheckResult(name(3), not v3_fail,
                    f"비-{type_name} {len(others)}p 에서 supportive≥2 동시 성립 {len(v3_fail)}건", v3_fail)
    )

    # ── V4: grouping + ordering against GT ───────────────────
    if grouping is None or ordering is None:
        results.append(CheckResult(name(4), False, "SKIPPED (--no-llm — 그룹핑 미수행)"))
    else:
        v4_fail = []
        instances = grouping.get("instances", [])
        if len(instances) != 1:
            v4_fail.append({"reason": f"instance 수 {len(instances)} (기대 1)",
                            "instances": [i.get("pages") for i in instances]})
        else:
            got = sorted(instances[0].get("pages", []))
            if got != gt_pages:
                v4_fail.append({"reason": "instance 페이지 집합 불일치", "got": got, "expected": gt_pages})
        if grouping.get("unresolved_pages"):
            v4_fail.append({"reason": "unresolved_pages 존재", "pages": grouping["unresolved_pages"]})
        if not v4_fail:
            ordered = ordering["instances"][0].get("ordered_pages", [])
            seq = [gt_by_page[p]["source_page"] for p in ordered]
            if seq != sorted(seq):
                v4_fail.append({"reason": "순서 불일치", "ordered_input_pages": ordered,
                                "gt_source_pages": seq})
        results.append(
            CheckResult(name(4), not v4_fail,
                        f"{gt_label} {type_name} 1 instance·GT 순서 일치" if not v4_fail
                        else "그룹핑/순서 불일치", v4_fail)
        )

    # ── V5 (CREDIT only): vendor-independent coverage, measure only ──
    if universal_only is not None:
        reached = [p for p in gt_pages if universal_only.get(p) in ("RULE_HIGH", "RULE_MEDIUM")]
        by_grade: dict[str, int] = {}
        for p in gt_pages:
            by_grade[universal_only.get(p, "MISSING")] = by_grade.get(universal_only.get(p, "MISSING"), 0) + 1
        results.append(
            CheckResult(
                name(5), True,
                f"[측정] universal 신호만으로 {len(reached)}/{len(gt_pages)}p 도달 "
                f"(벤더 레이어 제외 — 합격 기준 없음)",
                measurement={
                    "reached": len(reached), "total": len(gt_pages),
                    "pages_reached": reached,
                    "pages_missed": [p for p in gt_pages if p not in reached],
                    "grade_distribution": by_grade,
                },
            )
        )
    return results


def layer_contribution(classifications: list[dict], type_name: str) -> dict:
    """How many classified pages each signal layer contributed to."""
    per_layer: dict[str, set] = {}
    per_layer_alone: dict[str, set] = {}
    for c in classifications:
        if c.get("type") != type_name:
            continue
        key = (c["package"], c["page"])
        layers = {m.get("layer", "unspecified") for m in c.get("matches", [])}
        for lay in layers:
            per_layer.setdefault(lay, set()).add(key)
        if len(layers) == 1:
            per_layer_alone.setdefault(next(iter(layers)), set()).add(key)
    return {
        "pages_with_layer": {k: len(v) for k, v in sorted(per_layer.items())},
        "pages_with_only_that_layer": {k: len(v) for k, v in sorted(per_layer_alone.items())},
    }


def render_report(
    type_name: str,
    results: list[CheckResult],
    grouping: dict | None,
    ordering: dict | None,
    usage: dict | None,
    no_llm: bool,
    layers: dict | None = None,
    subtype_counts: dict | None = None,
    conflicts: list[dict] | None = None,
    warnings: list[str] | None = None,
) -> str:
    lines = [f"# {type_name} 파이프라인 리포트", ""]
    if warnings:
        lines += ["> ⚠️ 설정 경고", ""] + [f"> - {w}" for w in warnings] + [""]

    lines += ["## 검증 결과", "", "| # | 기준 | 결과 | 상세 |", "|---|---|---|---|"]
    for r in results:
        verdict = "측정" if r.measurement is not None else ("✅ PASS" if r.passed else "❌ FAIL")
        lines.append(f"| {r.name} | {r.detail} | {verdict} | {len(r.failures)}건 |")
    lines.append("")
    for r in results:
        if r.measurement is not None:
            lines += [f"### {r.name} 측정 상세", "", "```json",
                      json.dumps(r.measurement, ensure_ascii=False, indent=2), "```", ""]
        if r.failures:
            lines += [f"### {r.name} 실패 상세", "", "```json",
                      json.dumps(r.failures, ensure_ascii=False, indent=2), "```", ""]

    if layers:
        lines += ["## 신호 계층별 기여도", "",
                  "`pages_with_layer`: 해당 계층 신호가 하나라도 매칭된 페이지 수 (중복 집계).",
                  "`pages_with_only_that_layer`: 그 계층 신호만으로 잡힌 페이지 수.", "",
                  "```json", json.dumps(layers, ensure_ascii=False, indent=2), "```", ""]

    if subtype_counts is not None:
        lines += ["## subtype 분포", "", "```json",
                  json.dumps(subtype_counts, ensure_ascii=False, indent=2), "```", ""]

    if conflicts is not None:
        lines += ["## 유형 경합 페이지", ""]
        lines += (["```json", json.dumps(conflicts, ensure_ascii=False, indent=2), "```"]
                  if conflicts else ["없음"])
        lines.append("")

    lines += ["## 그룹핑 결과", ""]
    lines += (["SKIPPED (--no-llm)"] if no_llm or grouping is None
              else ["```json", json.dumps(grouping, ensure_ascii=False, indent=2), "```"])
    lines += ["", "## 순서 정렬 결과", ""]
    lines += (["SKIPPED (--no-llm)"] if no_llm or ordering is None
              else ["```json", json.dumps(ordering, ensure_ascii=False, indent=2), "```"])
    lines += ["", "## LLM 사용량 (이번 실행분)", ""]
    lines += (["```json", json.dumps(usage, ensure_ascii=False, indent=2), "```"] if usage
              else ["호출 없음"])
    lines.append("")
    return "\n".join(lines)
