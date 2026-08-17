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

CONFIG_PATH = Path(__file__).resolve().parent.parent.parent.parent / "config" / "expected_pages.yaml"


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
        # A type whose pages are meant to reach *different* grades declares
        # expected_paths instead of a flat list; the flat list is then its union
        # so V2/V3 keep excluding the same pages (income_doc.md §5).
        paths = entry.get("expected_paths") or {}
        expected = list(entry.get("expected", []))
        if paths and not expected:
            expected = sorted({p for pages in paths.values() for p in pages})
        out[label] = {
            "expected": expected,
            "expected_paths": {k: list(v) for k, v in paths.items()},
            "undecided": list(entry.get("undecided", [])),
            # image-only pages: judged by the VLM check, never by the rule check
            "expected_vlm": list(entry.get("expected_vlm", [])),
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


def _duplicate_marker_failures(label: str, grouping: dict, markers: dict) -> list[dict]:
    """Instances holding the same page-marker number twice.

    Two pages claiming to be "page 3 of 5" cannot belong to one physical
    document, so this is the objective form of the design's "duplicated marker
    set means separate instances" rule.

    Only markers carrying a denominator count. Bare ``Page N`` candidates are
    swamped by false positives — a deed reference like "Book 577, Page 401"
    looks identical to the extractor — and the design states the rule in terms
    of a complete set ("Page 1 of 5" appearing twice) anyway.
    """
    out = []
    for inst in grouping.get("instances", []):
        seen: dict[int, list[int]] = {}
        for page in inst.get("pages", []):
            for n, y in markers.get(page, []):
                if y is None:
                    continue
                seen.setdefault(n, []).append(page)
        dupes = {n: pgs for n, pgs in seen.items() if len(pgs) > 1}
        if dupes:
            out.append({
                "package": label,
                "instance_id": inst.get("instance_id"),
                "reason": "한 instance 안에 같은 마커 번호가 중복 — 설계 §4-1은 분리를 요구",
                "duplicated_markers": {str(n): pgs for n, pgs in sorted(dupes.items())},
            })
    return out


def run_verifications(
    type_name: str,
    classifications: list[dict],
    groupings: dict,
    orderings: dict,
    gt_rows: list[dict],
    gt_label: str,
    expected_pages: dict,
    prefix: str = "",
    universal_only: dict | None = None,
    gt_exclude_source_pages: list[int] | None = None,
    instance_expectations: dict | None = None,
    markers_by_page: dict | None = None,
    require_final_type: bool = False,
) -> list[CheckResult]:
    gt_pages = sorted(r["input_page"] for r in gt_rows if r["document_type"] == type_name)
    gt_by_page = {r["input_page"]: r for r in gt_rows}
    primary = _by_page(classifications, gt_label)
    grouping = groupings.get(gt_label)
    ordering = orderings.get(gt_label)

    # Pages the design excludes from V1 by name (title_report.md §5-1: the page
    # whose content was removed has no text evidence at all). They stay out of
    # the counter-example set too — they are of this type, just unprovable.
    excluded = {
        r["input_page"]
        for r in gt_rows
        if r["document_type"] == type_name
        and r["source_page"] in set(gt_exclude_source_pages or [])
    }
    v1_gt_pages = [p for p in gt_pages if p not in excluded]

    def name(n: int) -> str:
        return f"{prefix}V{n}"

    results: list[CheckResult] = []

    # ── V1: expected pages take their intended path ──────────
    path_specs = {lb: e["expected_paths"] for lb, e in expected_pages.items() if e["expected_paths"]}
    if path_specs:
        v1_fail, total = [], 0
        for label, spec in sorted(path_specs.items()):
            pages = _by_page(classifications, label)
            for want, page_list in sorted(spec.items()):
                for page in page_list:
                    total += 1
                    c = pages.get(page)
                    got = c["rule_grade"] if c else "MISSING"
                    if got != want.upper():
                        v1_fail.append({
                            "package": label, "page": page,
                            "expected_path": want.upper(), "got": got,
                            "signals": c and c.get("signals"),
                            "flags": c and c.get("flags"),
                        })
        results.append(
            CheckResult(
                name(1), not v1_fail,
                f"{type_name} 기대 {total}p 중 {total - len(v1_fail)}p 가 의도한 경로로 감 "
                "(유형마다 도달 등급이 다른 명세 — 전부 RULE_HIGH가 기준이 아님)",
                v1_fail,
            )
        )
    else:
        targets = [(gt_label, p, primary.get(p)) for p in v1_gt_pages]
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
        if label == gt_label:
            continue  # already covered above via the answer key
        skip = set(entry["expected"]) | set(entry["undecided"]) | set(entry["expected_vlm"])
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

    # ── V4: grouping + ordering against GT (+ per-package instance counts) ──
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
            if got != v1_gt_pages:
                v4_fail.append({"reason": "instance 페이지 집합 불일치",
                                "got": got, "expected": v1_gt_pages,
                                "note": f"검증 제외 페이지 {sorted(excluded)}는 기대값에서 뺐다"})
        if grouping.get("unresolved_pages"):
            v4_fail.append({"reason": "unresolved_pages 존재", "pages": grouping["unresolved_pages"]})
        if not v4_fail:
            ordered = ordering["instances"][0].get("ordered_pages", [])
            seq = [gt_by_page[p]["source_page"] for p in ordered]
            if seq != sorted(seq):
                v4_fail.append({"reason": "순서 불일치", "ordered_input_pages": ordered,
                                "gt_source_pages": seq})

        # Packages without an answer key can still assert a shape (instance
        # count, and whether the design requires the instances to be related).
        for label, spec in (instance_expectations or {}).items():
            g = groupings.get(label)
            if g is None:
                v4_fail.append({"package": label, "reason": "그룹핑 결과 없음 (범위 밖일 수 있음)"})
                continue
            got_n = len(g.get("instances", []))
            if got_n != spec["instances"]:
                v4_fail.append({"package": label,
                                "reason": f"instance 수 {got_n} (기대 {spec['instances']})",
                                "instances": [i.get("pages") for i in g.get("instances", [])]})
            if spec.get("require_related_to") and not any(
                i.get("related_to") for i in g.get("instances", [])
            ):
                v4_fail.append({"package": label, "reason": "related_to 기록 없음 (설계 §4-1 요구)"})
            # An instance count alone can be right for the wrong reason, so the
            # design's actual rule is checked directly: a marker number may not
            # repeat inside one instance (title_report.md §4-1).
            if spec.get("no_duplicate_markers"):
                v4_fail += _duplicate_marker_failures(
                    label, g, (markers_by_page or {}).get(label, {})
                )
            # Boilerplate shared by every copy cannot be attributed to one of
            # them, so "unassigned" is the correct output (title_report.md
            # §4-2-1). The page list lives in config, not here.
            if spec.get("vlm_pages_unresolved"):
                want = set(expected_pages.get(label, {}).get("expected_vlm", []))
                got = set(g.get("unresolved_pages", []))
                if want - got:
                    v4_fail.append({
                        "package": label,
                        "reason": "약관(공통 인쇄물) 페이지가 unresolved에 없음 — 설계 §4-2-1은 귀속 미정을 요구",
                        "expected_unresolved": sorted(want),
                        "got_unresolved": sorted(got),
                        "assigned_instead": {
                            i.get("instance_id"): sorted(set(i.get("pages", [])) & (want - got))
                            for i in g.get("instances", [])
                            if set(i.get("pages", [])) & (want - got)
                        },
                    })

        shape = f"{gt_label} 1 instance" + "".join(
            f" / {lb} {sp['instances']} instance" + ("+related_to" if sp.get("require_related_to") else "")
            for lb, sp in sorted((instance_expectations or {}).items())
        )
        results.append(
            CheckResult(name(4), not v4_fail,
                        f"{shape} · GT 순서 일치" if not v4_fail else "그룹핑/순서 불일치", v4_fail)
        )

    # ── V5 (CREDIT only): vendor-independent coverage, measure only ──
    if universal_only is not None:
        # Measured over the same population V1 judges, so the two are comparable.
        reached = [p for p in v1_gt_pages if universal_only.get(p) in ("RULE_HIGH", "RULE_MEDIUM")]
        by_grade: dict[str, int] = {}
        for p in v1_gt_pages:
            by_grade[universal_only.get(p, "MISSING")] = by_grade.get(universal_only.get(p, "MISSING"), 0) + 1
        results.append(
            CheckResult(
                name(5), True,
                f"[측정] universal 신호만으로 {len(reached)}/{len(v1_gt_pages)}p 도달 "
                f"(벤더 레이어 제외 — 합격 기준 없음)",
                measurement={
                    "reached": len(reached), "total": len(v1_gt_pages),
                    "pages_reached": reached,
                    "pages_missed": [p for p in v1_gt_pages if p not in reached],
                    "grade_distribution": by_grade,
                },
            )
        )

    # ── V6 (final type): rule + LLM together land on this type ──
    # A page can legitimately reach the type through the LLM rather than the
    # rules, so this asks about the end state, not the path.
    if require_final_type:
        final_fail = []
        for label, entry in sorted(expected_pages.items()):
            pages = _by_page(classifications, label)
            for page in entry["expected"]:
                c = pages.get(page)
                if c is None or c.get("type") != type_name:
                    final_fail.append({
                        "package": label, "page": page,
                        "rule_grade": c and c.get("rule_grade"),
                        "final_grade": c and c.get("grade"),
                        "got_type": c.get("type") if c else None,
                        "llm": c.get("llm") if c else None,
                    })
        total_final = sum(len(e["expected"]) for e in expected_pages.values())
        results.append(
            CheckResult(
                name(6), not final_fail,
                f"기대 {total_final}p 가 최종적으로 {type_name} 으로 확정 "
                f"({total_final - len(final_fail)}p 성공)",
                final_fail,
            )
        )

    # ── V6 (types with image pages): VLM classification ──────
    vlm_targets = [
        (label, p)
        for label, entry in expected_pages.items()
        for p in entry["expected_vlm"]
    ]
    if vlm_targets:
        v6_fail = []
        for label, page in vlm_targets:
            c = _by_page(classifications, label).get(page)
            if c is None or c.get("type") != type_name:
                v6_fail.append({
                    "package": label, "page": page,
                    "grade": c["grade"] if c else "MISSING",
                    "got_type": c.get("type") if c else None,
                    "vlm": c.get("llm") if c else None,
                })
        results.append(
            CheckResult(
                name(6), not v6_fail,
                f"스캔 {len(vlm_targets)}p 중 {len(vlm_targets) - len(v6_fail)}p "
                f"VLM이 {type_name}으로 판정",
                v6_fail,
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
    excluded_pages: list[dict] | None = None,
    vlm_pages: list[dict] | None = None,
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

    if vlm_pages is not None:
        lines += ["## VLM 판독 결과 (텍스트 레이어 없는 페이지)", ""]
        lines += (["```json", json.dumps(vlm_pages, ensure_ascii=False, indent=2), "```"]
                  if vlm_pages else ["대상 없음"])
        lines.append("")

    if excluded_pages is not None:
        lines += ["## 검증 제외 페이지의 실제 처리 결과", "",
                  "설계가 V1에서 제외하도록 지정한 페이지다. 제외했다고 처리 결과를 "
                  "감추지 않기 위해 여기에 그대로 기록한다.", ""]
        lines += (["```json", json.dumps(excluded_pages, ensure_ascii=False, indent=2), "```"]
                  if excluded_pages else ["대상 없음"])
        lines.append("")

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
