"""URLA pipeline: [1] classify -> [2] signal cards -> [3] LLM grouping -> [4] ordering + V1–V4.

Usage:
    uv run python -m docsplit.urla_pipeline --data-dir data --out-dir outputs
    options: --no-llm, --package {01,02,both} (default 01)

Notes:
- Rule classification ([1]) always runs on BOTH packages: V1–V3 span both and
  it is deterministic/free. --package scopes the LLM stages ([3][4]) and cards.
- Classification/grouping read only shuffled inputs; originals are touched
  exclusively by ground_truth.py (GT builder).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pymupdf

from .cards import build_card
from .classify import classify_page
from .evaluate import render_report, run_verifications
from .grouping import group_pages, order_instances
from .ground_truth import build_pkg01_ground_truth
from .llm import LLMClient, LLMDisabled
from .signals import load_policy

PACKAGE_FILES = {
    "01": ("01.sample01_shuffled.jsonl", "packages/01.sample01_shuffled.pdf"),
    "02": ("02.sample02_shuffled.jsonl", "packages/02.sample02_shuffled.pdf"),
}


def load_parsed(parsed_dir: Path, jsonl_name: str) -> list[dict]:
    path = parsed_dir / jsonl_name
    if not path.exists():
        raise SystemExit(
            f"{path} 없음 — 먼저 파싱을 실행하세요: uv run python -m docsplit.parse"
        )
    return [json.loads(l) for l in path.open(encoding="utf-8")]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", type=Path, default=Path("data"))
    ap.add_argument("--out-dir", type=Path, default=Path("outputs"))
    ap.add_argument("--package", choices=["01", "02", "both"], default="01")
    ap.add_argument("--no-llm", action="store_true")
    args = ap.parse_args()

    parsed_dir = args.out_dir / "parsed"
    urla_dir = args.out_dir / "urla"
    urla_dir.mkdir(parents=True, exist_ok=True)
    policy = load_policy("urla")
    scope = ["01", "02"] if args.package == "both" else [args.package]

    llm = None
    if not args.no_llm:
        try:
            llm = LLMClient(
                cache_dir=args.out_dir / "llm_cache",
                usage_path=args.out_dir / "llm_usage.json",
            )
        except LLMDisabled as e:
            sys.exit(str(e))

    # ── [1] classification (both packages, rule-only) ─────────
    classifications: list[dict] = []
    pages_by_pkg: dict[str, dict[int, str]] = {}
    signal_results: dict[tuple[str, int], object] = {}
    page_texts: dict[tuple[str, int], object] = {}
    for pkg, (jsonl_name, _) in PACKAGE_FILES.items():
        recs = load_parsed(parsed_dir, jsonl_name)
        pages_by_pkg[pkg] = {r["page_index"]: r["raw_text"] for r in recs}
        for rec in recs:
            cls, sig, ptext = classify_page(pkg, rec["page_index"], rec["raw_text"], policy)
            signal_results[(pkg, rec["page_index"])] = sig
            page_texts[(pkg, rec["page_index"])] = ptext
            classifications.append(cls.to_dict())

    # DEFER_LLM resolution (in-scope packages only)
    for c in classifications:
        if c["grade"] != "DEFER_LLM" or c["package"] not in scope:
            continue
        if llm is None:
            continue  # --no-llm: 미판정으로 남김
        parsed = llm.complete_json(
            stage="classify_page",
            prompt_name="classify_page",
            variables={
                "candidate_type": policy["type"],
                "signal_summary": json.dumps(c["signals"], ensure_ascii=False),
                "page_text": pages_by_pkg[c["package"]][c["page"]],
            },
        )
        c["llm"] = parsed
        if parsed.get("type") == policy["type"]:
            c["type"], c["grade"] = policy["type"], "LLM"
            c["subtype"] = c["subtype"] or parsed.get("subtype")
        elif parsed.get("type") == "UNRESOLVED":
            c["grade"] = "LLM_UNRESOLVED"
        else:
            c["type"], c["grade"] = None, "LLM"

    with (urla_dir / "classification.jsonl").open("w", encoding="utf-8") as f:
        for c in classifications:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    n_urla = sum(1 for c in classifications if c["type"] == policy["type"])
    print(f"[1] 판정 완료: {len(classifications)}p 중 URLA {n_urla}p")

    # ── [2] signal cards (in-scope URLA pages) ────────────────
    cards_by_pkg: dict[str, list] = {}
    with (urla_dir / "cards.jsonl").open("w", encoding="utf-8") as f:
        for pkg in scope:
            pdf = pymupdf.open(args.data_dir / PACKAGE_FILES[pkg][1])
            cards = []
            for c in classifications:
                if c["package"] != pkg or c["type"] != policy["type"]:
                    continue
                card = build_card(
                    pkg, c["page"], page_texts[(pkg, c["page"])],
                    signal_results[(pkg, c["page"])], c["subtype"], policy,
                    pdf[c["page"]],
                )
                cards.append(card)
                f.write(json.dumps(card.to_dict(), ensure_ascii=False) + "\n")
            pdf.close()
            cards_by_pkg[pkg] = cards
            print(f"[2] 신호 카드: pkg{pkg} {len(cards)}장")

    # ── [3][4] grouping + ordering ────────────────────────────
    groupings, orderings = {}, {}
    if llm is None:
        (urla_dir / "grouping.json").write_text(
            json.dumps({"status": "SKIPPED", "reason": "--no-llm"}, ensure_ascii=False), encoding="utf-8"
        )
        (urla_dir / "ordering.json").write_text(
            json.dumps({"status": "SKIPPED", "reason": "--no-llm"}, ensure_ascii=False), encoding="utf-8"
        )
        print("[3][4] SKIPPED (--no-llm)")
    else:
        for pkg in scope:
            g = group_pages(pkg, cards_by_pkg[pkg], pages_by_pkg[pkg], policy, llm)
            groupings[pkg] = g
            orderings[pkg] = order_instances(g, cards_by_pkg[pkg], policy)
            print(f"[3][4] pkg{pkg}: instance {len(g.get('instances', []))}개, "
                  f"unresolved {len(g.get('unresolved_pages', []))}p")
        (urla_dir / "grouping.json").write_text(
            json.dumps(groupings, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (urla_dir / "ordering.json").write_text(
            json.dumps(orderings, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # ── GT + V1–V4 ────────────────────────────────────────────
    gt_rows = build_pkg01_ground_truth(parsed_dir, args.out_dir / "ground_truth" / "pkg01.jsonl")
    results = run_verifications(
        classifications, groupings.get("01"), orderings.get("01"), gt_rows
    )
    usage = None
    usage_path = args.out_dir / "llm_usage.json"
    if usage_path.exists():
        usage = json.loads(usage_path.read_text(encoding="utf-8"))
    report = render_report(results, groupings.get("01"), orderings.get("01"), usage, args.no_llm)
    (urla_dir / "report.md").write_text(report, encoding="utf-8")
    for r in results:
        print(f"{r.name}: {'PASS' if r.passed else 'FAIL'} — {r.detail}")
    print(f"report: {urla_dir / 'report.md'}")


if __name__ == "__main__":
    main()
