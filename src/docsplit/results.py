"""Final deliverables under results/ — the part a reviewer reads.

Deliberately free of page content: evidence quotes can carry borrower names,
addresses and amounts, so they stay in outputs/ (gitignored) and only
structure, grades and counts come here.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

TYPES = ["URLA_1003", "CREDIT_REPORT", "TITLE_REPORT", "INCOME_DOC", "OTHER"]


def write_classification_csv(verdicts: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["page", "page_display", "type", "subtype", "grade",
                    "rule_grade", "decided_by"])
        for v in sorted(verdicts, key=lambda v: v["page"]):
            w.writerow([v["page"], v["page"] + 1, v["type"] or "", v["subtype"] or "",
                        v["grade"], v["rule_grade"], v["decided_by"]])


def write_documents_json(groupings: dict, orderings: dict, path: Path) -> None:
    """Instances per type, with ordering and whatever stayed unresolved."""
    docs = []
    for type_name in sorted(groupings):
        g = groupings[type_name]
        order_by_id = {
            i.get("instance_id"): i for i in orderings.get(type_name, {}).get("instances", [])
        }
        for inst in g.get("instances", []):
            o = order_by_id.get(inst.get("instance_id"), {})
            entry = {
                "type": type_name,
                "instance_id": inst.get("instance_id"),
                "pages": sorted(inst.get("pages", [])),
                "ordered_pages": o.get("ordered_pages", []),
                "ordering_method": o.get("method"),
                "ordering_unresolved": o.get("unresolved", []),
            }
            if inst.get("related_to"):
                entry["related_to"] = inst["related_to"]
            docs.append(entry)
    unresolved = {
        t: sorted(g.get("unresolved_pages", []))
        for t, g in groupings.items()
        if g.get("unresolved_pages")
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"documents": docs, "unresolved_pages": unresolved},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f


def score_against_gt(verdicts: list[dict], gt_rows: list[dict]) -> dict:
    """Accuracy, per-type P/R/F1 and a confusion table."""
    truth = {r["input_page"]: r["document_type"] for r in gt_rows}
    pred = {v["page"]: (v["type"] or "UNRESOLVED") for v in verdicts if v["page"] in truth}
    correct = sum(1 for p, t in truth.items() if pred.get(p) == t)

    labels = sorted(set(truth.values()) | set(pred.values()))
    per_type, f1s = {}, []
    for label in labels:
        tp = sum(1 for p, t in truth.items() if t == label and pred.get(p) == label)
        fp = sum(1 for p, t in truth.items() if t != label and pred.get(p) == label)
        fn = sum(1 for p, t in truth.items() if t == label and pred.get(p) != label)
        p_, r_, f_ = _prf(tp, fp, fn)
        support = sum(1 for t in truth.values() if t == label)
        per_type[label] = {"precision": round(p_, 4), "recall": round(r_, 4),
                           "f1": round(f_, 4), "support": support}
        if support:
            f1s.append(f_)

    confusion: dict[str, Counter] = defaultdict(Counter)
    for page, t in truth.items():
        confusion[t][pred.get(page, "MISSING")] += 1
    mistakes = [
        {"page": page, "truth": t, "predicted": pred.get(page, "MISSING")}
        for page, t in sorted(truth.items())
        if pred.get(page) != t
    ]
    return {
        "total": len(truth),
        "correct": correct,
        "accuracy": round(correct / len(truth), 4) if truth else 0.0,
        "macro_f1": round(sum(f1s) / len(f1s), 4) if f1s else 0.0,
        "per_type": per_type,
        "confusion": {k: dict(v) for k, v in sorted(confusion.items())},
        "mistakes": mistakes,
    }


def write_evaluation_md(label: str, scored: dict, groupings: dict, orderings: dict,
                        gt_rows: list[dict], path: Path) -> None:
    truth = {r["input_page"]: r for r in gt_rows}
    lines = [
        f"# 패키지 {label} 검증 결과 (정답 대조)", "",
        f"- 페이지 {scored['total']}장 중 **{scored['correct']}장 정확** "
        f"(accuracy **{scored['accuracy']:.3f}**)",
        f"- macro F1: **{scored['macro_f1']:.3f}**", "",
        "## 유형별 정밀도·재현율", "",
        "| 유형 | precision | recall | F1 | 정답 장수 |", "|---|---|---|---|---|",
    ]
    for t, m in scored["per_type"].items():
        lines.append(f"| {t} | {m['precision']:.3f} | {m['recall']:.3f} | "
                     f"{m['f1']:.3f} | {m['support']} |")

    lines += ["", "## 혼동 행렬 (정답 → 예측)", ""]
    for t, row in scored["confusion"].items():
        lines.append(f"- **{t}** → " + ", ".join(f"{k} {v}장" for k, v in sorted(row.items())))

    lines += ["", "## 오분류 상세", ""]
    if scored["mistakes"]:
        lines += ["| 페이지(0-based) | 정답 | 예측 |", "|---|---|---|"]
        lines += [f"| {m['page']} | {m['truth']} | {m['predicted']} |"
                  for m in scored["mistakes"]]
    else:
        lines.append("없음")

    lines += ["", "## 그룹핑·정렬", "",
              "정답 원본의 페이지 순서와 비교한다. `순서 일치`는 복원된 순서가 "
              "원본 순서와 같다는 뜻이다.", ""]
    for type_name in sorted(groupings):
        g, o = groupings[type_name], orderings.get(type_name, {})
        lines.append(f"### {type_name}")
        for inst in g.get("instances", []):
            entry = next((x for x in o.get("instances", [])
                          if x.get("instance_id") == inst.get("instance_id")), {})
            ordered = entry.get("ordered_pages", [])
            seq = [truth[p]["source_page"] for p in ordered if p in truth]
            verdict = "✅ 순서 일치" if seq == sorted(seq) else "❌ 순서 불일치"
            lines.append(f"- `{inst.get('instance_id')}`: {len(inst.get('pages', []))}장, "
                         f"정렬 {entry.get('method', '—')} → {verdict}"
                         + (f", 미해결 {entry['unresolved']}" if entry.get("unresolved") else ""))
        if g.get("unresolved_pages"):
            lines.append(f"- 그룹핑 미배정: {sorted(g['unresolved_pages'])}")
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_summary_md(label: str, verdicts: list[dict], groupings: dict, orderings: dict,
                     scored: dict | None, usage: dict | None, cost: dict | None,
                     path: Path) -> None:
    by_type = Counter(v["type"] or "UNRESOLVED" for v in verdicts)
    by_decider = Counter(v["decided_by"] for v in verdicts)
    lines = [
        f"# 패키지 {label} 요약", "",
        f"전체 **{len(verdicts)}페이지**.", "",
        "## 유형 분포", "", "| 유형 | 페이지 수 |", "|---|---|",
    ]
    lines += [f"| {t} | {n} |" for t, n in by_type.most_common()]

    lines += ["", "## 판정 경로", "", "| 경로 | 페이지 수 |", "|---|---|"]
    lines += [f"| {d} | {n} |" for d, n in sorted(by_decider.items())]

    if scored:
        lines += ["", "## 정답 대조", "",
                  f"- accuracy **{scored['accuracy']:.3f}** "
                  f"({scored['correct']}/{scored['total']})",
                  f"- macro F1 **{scored['macro_f1']:.3f}**",
                  "- 상세는 `evaluation.md` 참조"]
    else:
        lines += ["", "## 정답 대조", "",
                  "이 패키지는 정답 원본이 제공되지 않아 대조하지 않았다 — 분류 결과만 산출한다."]

    lines += ["", "## 문서 구성", ""]
    total_docs = sum(len(g.get("instances", [])) for g in groupings.values())
    lines.append(f"총 **{total_docs}개 문서 instance**로 묶였다.")
    lines.append("")
    for type_name in sorted(groupings):
        g, o = groupings[type_name], orderings.get(type_name, {})
        insts = g.get("instances", [])
        lines.append(f"- **{type_name}**: {len(insts)}개 instance "
                     f"({', '.join(str(len(i.get('pages', []))) + '장' for i in insts) or '—'})")
        for inst in insts:
            entry = next((x for x in o.get("instances", [])
                          if x.get("instance_id") == inst.get("instance_id")), {})
            if entry.get("unresolved"):
                lines.append(f"    - `{inst.get('instance_id')}` 순서 미해결: {entry['unresolved']}")
        if g.get("unresolved_pages"):
            lines.append(f"    - 어느 instance에도 배정하지 못한 페이지: "
                         f"{sorted(g['unresolved_pages'])}")

    unresolved_pages = [v["page"] for v in verdicts if not v["type"]]
    lines += ["", "## 미해결 페이지", ""]
    lines.append(f"유형을 확정하지 못한 페이지: {sorted(unresolved_pages) or '없음'}")

    if usage:
        lines += ["", "## LLM 사용량 (이번 실행분)", "",
                  "| 단계 | 호출 | 캐시 적중 | prompt 토큰 | completion 토큰 |",
                  "|---|---|---|---|---|"]
        for stage, u in sorted(usage.items()):
            lines.append(f"| {stage} | {u['calls']} | {u['cache_hits']} | "
                         f"{u['prompt_tokens']:,} | {u['completion_tokens']:,} |")
        if cost:
            lines += ["", f"추정 비용: **${cost['total_usd']:.4f}** "
                          f"(모델 {cost['model']}, 단가 1M 토큰당 "
                          f"입력 ${cost['input_per_1m']}/출력 ${cost['output_per_1m']} 가정)"]
        if not any(u["calls"] for u in usage.values()):
            lines += ["", "> 호출 0건은 **전부 캐시로 처리됐다는 뜻**이다 "
                          "(`outputs/llm_cache/`). 캐시가 없는 첫 실행의 실측치는 "
                          "`outputs/llm_usage.json` 의 `cumulative` 에 누적된다."]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
