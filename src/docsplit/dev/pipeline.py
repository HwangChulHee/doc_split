"""Shared pipeline: [1] classify -> [2] signal cards -> [3] grouping -> [4] ordering + checks.

One implementation drives every document type; the type is selected by policy
name (``docsplit.dev.urla_pipeline`` / ``docsplit.dev.credit_pipeline`` are thin entry
points). Nothing here is type-specific — phrases, thresholds, card fields,
prompts, and fallback ordering all come from the policy file.

Notes:
- Rule classification ([1]) always runs on ALL packages: the checks span them
  and it is deterministic and free. ``--package`` scopes the LLM stages.
- Classification and grouping read shuffled inputs only; the original documents
  are touched exclusively by ground_truth.py.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

import pymupdf

from ..rules.cards import apply_vlm_extract, build_card
from ..rules.classify import classify_page
from .evaluate import (
    layer_contribution,
    load_expected_pages,
    render_report,
    run_verifications,
)
from ..llm.grouping import group_pages, order_instances
from ..ingest.discover import discover_inputs
from ..output.ground_truth import build_ground_truth
from ..llm.client import LLMClient, LLMDisabled
from ..rules.normalize import PageText
from ..ingest.pdf_parser import render_page_png, slugify
from ..rules.signals import available_policies, evaluate_universal_only, load_policy
from ..rules.classify import grade_for

PACKAGE_LABEL_RE = re.compile(r"^(\d+)\.")
VLM_DPI = 150  # title_report.md §7 — enough to read headers/footers off a scan


def discover_packages(data_dir: Path, parsed_dir: Path) -> dict[str, tuple[Path, Path]]:
    """Map package label -> (input PDF, parsed JSONL).

    Labels come from a leading ``NN.`` in the file name, else the 1-based
    position, so package file names are never hardcoded.
    """
    packages: dict[str, tuple[Path, Path]] = {}
    for i, pdf in enumerate(sorted((data_dir / "packages").glob("*.pdf")), start=1):
        m = PACKAGE_LABEL_RE.match(pdf.name)
        label = m.group(1) if m else f"{i:02d}"
        packages[label] = (pdf, parsed_dir / f"{slugify(pdf.name)}.jsonl")
    if not packages:
        raise SystemExit(f"{data_dir / 'packages'} 에 PDF가 없습니다.")
    return packages


def load_parsed(path: Path) -> list[dict]:
    if not path.exists():
        raise SystemExit(f"{path} 없음 — 먼저 파싱을 실행하세요: uv run python -m docsplit.ingest.parse")
    return [json.loads(l) for l in path.open(encoding="utf-8")]


def build_arg_parser(description: str) -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=description)
    ap.add_argument("--data-dir", type=Path, default=Path("data"))
    ap.add_argument("--out-dir", type=Path, default=Path("outputs"))
    ap.add_argument("--package", default="01",
                    help="package label (leading NN. of the file name), or 'both'")
    ap.add_argument("--no-llm", action="store_true")
    return ap


def run(policy_name: str, out_subdir: str, check_prefix: str, args: argparse.Namespace) -> None:
    policy = load_policy(policy_name)
    type_name = policy["type"]
    competing = [load_policy(n) for n in available_policies() if n != policy_name]
    # The VLM sees an image with no prior rule evidence, so it is offered every
    # type — including ones no policy exists for yet (title_report.md §7).
    all_types = sorted({type_name, *(p["type"] for p in competing),
                        "INCOME_DOC", "OTHER"})

    parsed_dir = args.out_dir / "parsed"
    out_dir = args.out_dir / out_subdir
    out_dir.mkdir(parents=True, exist_ok=True)

    packages = discover_packages(args.data_dir, parsed_dir)
    if args.package == "both":
        scope = sorted(packages)
    elif args.package in packages:
        scope = [args.package]
    else:
        raise SystemExit(
            f"패키지 '{args.package}' 없음 — 사용 가능: {', '.join(sorted(packages))} 또는 both"
        )
    gt_label = sorted(packages)[0]  # the answer key exists for the first package

    llm = None
    if not args.no_llm:
        try:
            llm = LLMClient(cache_dir=args.out_dir / "llm_cache",
                            usage_path=args.out_dir / "llm_usage.json")
        except LLMDisabled as e:
            sys.exit(str(e))

    # ── [1] classification (all packages, rule-only) ──────────
    classifications: list[dict] = []
    pages_by_pkg: dict[str, dict[int, str]] = {}
    signal_results: dict[tuple[str, int], object] = {}
    page_texts: dict[tuple[str, int], object] = {}
    universal_only: dict[str, dict[int, str]] = {}
    for pkg, (_, jsonl_path) in sorted(packages.items()):
        recs = load_parsed(jsonl_path)
        pages_by_pkg[pkg] = {r["page_index"]: r["raw_text"] for r in recs}
        universal_only[pkg] = {}
        for rec in recs:
            cls, sig, ptext = classify_page(
                pkg, rec["page_index"], rec["raw_text"], policy, competing
            )
            signal_results[(pkg, rec["page_index"])] = sig
            page_texts[(pkg, rec["page_index"])] = ptext
            classifications.append(cls.to_dict())
            # vendor-independent coverage probe (C-V5), rule-only and free
            if ptext.fulltext:
                uni_res = evaluate_universal_only(ptext, policy)
                universal_only[pkg][rec["page_index"]] = grade_for(uni_res, policy)[0]

    # deferred pages resolved by the LLM (in-scope packages only)
    subtype_options = sorted(
        {
            name
            for vblock in (policy.get("vendors") or {}).values()
            for name in (vblock.get("subtypes") or {})
        }
        | set((policy.get("subtypes", {}).get("suffix_map") or {}).values())
    )
    llm_cfg = policy.get("llm", {})
    # Some subgroups carry no rule signal by nature rather than by omission
    # (income_doc.md §1: a P&L scores zero on a 32-probe vocabulary). A policy
    # can opt into sending those pages to the LLM too.
    llm_grades = {"DEFER_LLM"}
    if llm_cfg.get("classify_on_no_signal"):
        llm_grades.add("NO_SIGNAL")

    for c in classifications:
        if c["grade"] not in llm_grades or c["package"] not in scope or llm is None:
            continue
        candidates = c["flags"].get("type_conflict") or [type_name]
        if llm_cfg.get("offer_rival_types"):
            # Let the model choose against the types that also claim the page,
            # instead of only confirming or rejecting this one.
            candidates = sorted(set(candidates) | set(c["flags"].get("rival_grades", {})))
        if c["grade"] == "NO_SIGNAL":
            # Nothing claimed this page, so narrowing the choice to one type
            # would be arbitrary. OTHER is reachable only here — it has no
            # policy file by design (income_doc handoff §4).
            candidates = all_types
        parsed = llm.complete_json(
            stage="classify_page",
            prompt_name="classify_page",
            variables={
                "candidate_types": ", ".join(candidates),
                "reason": "TYPE_CONFLICT" if c["flags"].get("type_conflict") else c["grade"],
                "signal_summary": json.dumps(c["signals"], ensure_ascii=False),
                "subtype_options": ", ".join(subtype_options) or "(없음)",
                "page_text": pages_by_pkg[c["package"]][c["page"]],
            },
        )
        c["llm"] = parsed
        if parsed.get("type") == type_name:
            c["type"], c["grade"] = type_name, "LLM"
            c["subtype"] = c["subtype"] or parsed.get("subtype")
        elif parsed.get("type") in (None, "UNRESOLVED"):
            c["grade"] = "LLM_UNRESOLVED"
        else:
            # Includes OTHER, which is a verdict rather than a fallback: no
            # policy file exists for it by design (income_doc handoff §4).
            c["type"], c["grade"] = parsed.get("type"), "LLM"

    # ── [1b] VLM: pages with no text layer at all ─────────────
    # Rendering carries the page rotation, so no separate correction is needed.
    vlm_extracts: dict[tuple[str, int], dict] = {}
    for c in classifications:
        if c["grade"] != "DEFER_VLM" or c["package"] not in scope or llm is None:
            continue
        with pymupdf.open(packages[c["package"]][0]) as pdf:
            png = render_page_png(pdf[c["page"]], VLM_DPI)
        parsed = llm.complete_json_vision(
            stage="classify_page_vision",
            prompt_name="classify_page_vision",
            variables={
                "candidate_types": "\n".join(f"- {t}" for t in all_types),
                "package": c["package"],
                "page": str(c["page"]),
            },
            image_png=png,
        )
        c["llm"] = parsed
        if parsed.get("type") == type_name:
            c["type"], c["grade"] = type_name, "VLM"
            c["subtype"] = parsed.get("subtype")
            vlm_extracts[(c["package"], c["page"])] = parsed.get("extracted") or {}
        elif parsed.get("type") in (None, "UNRESOLVED"):
            c["grade"] = "VLM_UNRESOLVED"
        else:
            c["type"], c["grade"] = None, "VLM"

    with (out_dir / "classification.jsonl").open("w", encoding="utf-8") as f:
        for c in classifications:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    n_typed = sum(1 for c in classifications if c["type"] == type_name)
    print(f"[1] 판정 완료: {len(classifications)}p 중 {type_name} {n_typed}p")

    # ── [2] signal cards (in-scope pages of this type) ────────
    cards_by_pkg: dict[str, list] = {}
    with (out_dir / "cards.jsonl").open("w", encoding="utf-8") as f:
        for pkg in scope:
            pdf = pymupdf.open(packages[pkg][0])
            cards = []
            for c in classifications:
                if c["package"] != pkg or c["type"] != type_name:
                    continue
                card = build_card(
                    pkg, c["page"], page_texts[(pkg, c["page"])],
                    signal_results[(pkg, c["page"])], c["subtype"], policy, pdf[c["page"]],
                )
                extracted = vlm_extracts.get((pkg, c["page"]))
                if extracted:  # image page: the card is empty without this
                    apply_vlm_extract(card, extracted)
                cards.append(card)
                f.write(json.dumps(card.to_dict(), ensure_ascii=False) + "\n")
            pdf.close()
            cards_by_pkg[pkg] = cards
            print(f"[2] 신호 카드: pkg{pkg} {len(cards)}장")

    # ── [3][4] grouping + ordering ────────────────────────────
    groupings, orderings = {}, {}
    if llm is None:
        skipped = json.dumps({"status": "SKIPPED", "reason": "--no-llm"}, ensure_ascii=False)
        (out_dir / "grouping.json").write_text(skipped, encoding="utf-8")
        (out_dir / "ordering.json").write_text(skipped, encoding="utf-8")
        print("[3][4] SKIPPED (--no-llm)")
    else:
        for pkg in scope:
            if not cards_by_pkg[pkg]:
                print(f"[3][4] pkg{pkg}: 대상 페이지 없음 — 건너뜀")
                continue
            g = group_pages(pkg, cards_by_pkg[pkg], pages_by_pkg[pkg], policy, llm)
            groupings[pkg] = g
            orderings[pkg] = order_instances(g, cards_by_pkg[pkg], policy)
            print(f"[3][4] pkg{pkg}: instance {len(g.get('instances', []))}개, "
                  f"unresolved {len(g.get('unresolved_pages', []))}p")
        (out_dir / "grouping.json").write_text(
            json.dumps(groupings, ensure_ascii=False, indent=2), encoding="utf-8")
        (out_dir / "ordering.json").write_text(
            json.dumps(orderings, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── GT + checks ───────────────────────────────────────────
    # Answer-key files are recognized the same way the unified CLI recognizes
    # them, so the two paths never disagree about what the originals are.
    answer_keys = {f.path.name: f.doc_type for f in discover_inputs(args.data_dir).answer_keys}
    gt_rows, gt_coverage = build_ground_truth(
        answer_keys, parsed_dir, packages[gt_label][1],
        args.out_dir / "ground_truth" / f"pkg{gt_label}.jsonl",
    )
    if gt_coverage < 1.0:
        print(f"⚠️  패키지 {gt_label} 의 정답 매칭률이 {gt_coverage:.0%} 입니다 — 검증이 부분적입니다.")
    expected, warnings = load_expected_pages(type_name, sorted(packages))
    for w in warnings:
        print(f"⚠️  {w}")

    verify_cfg = policy.get("verification", {})
    results = run_verifications(
        type_name, classifications, groupings, orderings,
        gt_rows, gt_label=gt_label, expected_pages=expected, prefix=check_prefix,
        universal_only=universal_only.get(gt_label) if policy.get("vendors") else None,
        gt_exclude_source_pages=verify_cfg.get("gt_exclude_source_pages"),
        instance_expectations=verify_cfg.get("instance_expectations"),
        require_final_type=verify_cfg.get("require_final_type", False),
        markers_by_page={
            pkg: {c.page: [(m["n"], m["y"]) for m in c.page_marker_candidates] for c in cards}
            for pkg, cards in cards_by_pkg.items()
        },
    )

    excluded_src = set(verify_cfg.get("gt_exclude_source_pages") or [])
    excluded_input = {
        r["input_page"] for r in gt_rows
        if r["document_type"] == type_name and r["source_page"] in excluded_src
    }
    excluded_pages = [
        c for c in classifications
        if c["package"] == gt_label and c["page"] in excluded_input
    ]
    vlm_pages = [c for c in classifications if c["grade"].startswith("VLM")
                 or (c.get("llm") and c["grade"] == "DEFER_VLM")]

    subtype_counts = dict(
        Counter(
            f"{c['package']}:{c['subtype']}"
            for c in classifications
            if c["type"] == type_name
        )
    )
    conflicts = [
        {"package": c["package"], "page": c["page"], "types": c["flags"]["type_conflict"]}
        for c in classifications
        if c["flags"].get("type_conflict")
    ]
    report = render_report(
        type_name, results, groupings.get(gt_label), orderings.get(gt_label),
        llm.this_run if llm else None, args.no_llm,
        layers=layer_contribution(classifications, type_name),
        subtype_counts=subtype_counts,
        conflicts=conflicts,
        warnings=warnings,
        excluded_pages=excluded_pages if excluded_src else None,
        vlm_pages=vlm_pages if any(c["grade"] == "DEFER_VLM" or
                                   c["grade"].startswith("VLM") for c in classifications) else None,
    )
    (out_dir / "report.md").write_text(report, encoding="utf-8")
    for r in results:
        verdict = "MEASURE" if r.measurement is not None else ("PASS" if r.passed else "FAIL")
        print(f"{r.name}: {verdict} — {r.detail}")
    print(f"report: {out_dir / 'report.md'}")
