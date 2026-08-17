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
from dataclasses import dataclass, field
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
from ..ingest.pdf_parser import slugify
from ..ingest.render import render_upright_png
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


@dataclass
class _Run:
    """One invocation's settings, resolved from the policy and the arguments."""

    policy: dict
    type_name: str
    competing: list[dict]
    all_types: list[str]
    packages: dict[str, tuple[Path, Path]]
    scope: list[str]
    gt_label: str
    parsed_dir: Path
    out_dir: Path
    llm: LLMClient | None


@dataclass
class _Classified:
    """Stage [1] output. Verdicts are dicts so later stages can annotate them."""

    rows: list[dict] = field(default_factory=list)
    pages_by_pkg: dict[str, dict[int, str]] = field(default_factory=dict)
    signal_results: dict[tuple[str, int], object] = field(default_factory=dict)
    page_texts: dict[tuple[str, int], PageText] = field(default_factory=dict)
    universal_only: dict[str, dict[int, str]] = field(default_factory=dict)


def run(policy_name: str, out_subdir: str, check_prefix: str, args: argparse.Namespace) -> None:
    r = _setup(policy_name, out_subdir, args)

    classified = _classify_by_rules(r)
    _resolve_deferred_by_llm(r, classified)
    vlm_extracts = _resolve_image_pages_by_vlm(r, classified)
    _write_classifications(r, classified)

    cards_by_pkg = _build_cards(r, classified, vlm_extracts)
    groupings, orderings = _group_and_order(r, classified, cards_by_pkg)

    _verify_and_report(r, args, check_prefix, classified, cards_by_pkg, groupings, orderings)


def _setup(policy_name: str, out_subdir: str, args: argparse.Namespace) -> _Run:
    policy = load_policy(policy_name)
    type_name = policy["type"]
    competing = [load_policy(n) for n in available_policies() if n != policy_name]

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

    llm = None
    if not args.no_llm:
        try:
            llm = LLMClient(cache_dir=args.out_dir / "llm_cache",
                            usage_path=args.out_dir / "llm_usage.json")
        except LLMDisabled as e:
            sys.exit(str(e))

    return _Run(
        policy=policy,
        type_name=type_name,
        competing=competing,
        # The VLM sees an image with no prior rule evidence, so it is offered
        # every type — including ones no policy exists for yet (§7 of title_report).
        all_types=sorted({type_name, *(p["type"] for p in competing),
                          "INCOME_DOC", "OTHER"}),
        packages=packages,
        scope=scope,
        gt_label=sorted(packages)[0],  # the answer key exists for the first package
        parsed_dir=parsed_dir,
        out_dir=out_dir,
        llm=llm,
    )


# ── [1] classification (all packages, rule-only) ──────────────
def _classify_by_rules(r: _Run) -> _Classified:
    out = _Classified()
    for pkg, (_, jsonl_path) in sorted(r.packages.items()):
        recs = load_parsed(jsonl_path)
        out.pages_by_pkg[pkg] = {rec["page_index"]: rec["raw_text"] for rec in recs}
        out.universal_only[pkg] = {}
        for rec in recs:
            cls, sig, ptext = classify_page(
                pkg, rec["page_index"], rec["raw_text"], r.policy, r.competing
            )
            out.signal_results[(pkg, rec["page_index"])] = sig
            out.page_texts[(pkg, rec["page_index"])] = ptext
            out.rows.append(cls.to_dict())
            # vendor-independent coverage probe (C-V5), rule-only and free
            if ptext.fulltext:
                uni_res = evaluate_universal_only(ptext, r.policy)
                out.universal_only[pkg][rec["page_index"]] = grade_for(uni_res, r.policy)[0]
    return out


def _subtype_options(policy: dict) -> list[str]:
    return sorted(
        {
            name
            for vblock in (policy.get("vendors") or {}).values()
            for name in (vblock.get("subtypes") or {})
        }
        | set((policy.get("subtypes", {}).get("suffix_map") or {}).values())
    )


def _llm_candidates(r: _Run, c: dict, llm_cfg: dict) -> list[str]:
    """Which types this page is offered. Never an arbitrary single choice."""
    if c["grade"] == "NO_SIGNAL":
        # Nothing claimed this page, so narrowing the choice to one type would
        # be arbitrary. OTHER is reachable only here — it has no policy file by
        # design (income_doc handoff §4).
        return r.all_types
    candidates = c["flags"].get("type_conflict") or [r.type_name]
    if llm_cfg.get("offer_rival_types"):
        # Let the model choose against the types that also claim the page,
        # instead of only confirming or rejecting this one.
        candidates = sorted(set(candidates) | set(c["flags"].get("rival_grades", {})))
    return candidates


def _apply_text_answer(c: dict, parsed: dict, type_name: str) -> None:
    c["llm"] = parsed
    if parsed.get("type") == type_name:
        c["type"], c["grade"] = type_name, "LLM"
        c["subtype"] = c["subtype"] or parsed.get("subtype")
    elif parsed.get("type") in (None, "UNRESOLVED"):
        c["grade"] = "LLM_UNRESOLVED"
    else:
        # Includes OTHER, which is a verdict rather than a fallback: no policy
        # file exists for it by design (income_doc handoff §4).
        c["type"], c["grade"] = parsed.get("type"), "LLM"


def _resolve_deferred_by_llm(r: _Run, classified: _Classified) -> None:
    """Deferred pages of in-scope packages, resolved in place."""
    llm_cfg = r.policy.get("llm", {})
    # Some subgroups carry no rule signal by nature rather than by omission
    # (income_doc.md §1: a P&L scores zero on a 32-probe vocabulary). A policy
    # can opt into sending those pages to the LLM too.
    llm_grades = {"DEFER_LLM"}
    if llm_cfg.get("classify_on_no_signal"):
        llm_grades.add("NO_SIGNAL")
    subtype_options = _subtype_options(r.policy)

    for c in classified.rows:
        if c["grade"] not in llm_grades or c["package"] not in r.scope or r.llm is None:
            continue
        parsed = r.llm.complete_json(
            stage="classify_page",
            prompt_name="classify_page",
            variables={
                "candidate_types": ", ".join(_llm_candidates(r, c, llm_cfg)),
                "reason": "TYPE_CONFLICT" if c["flags"].get("type_conflict") else c["grade"],
                "signal_summary": json.dumps(c["signals"], ensure_ascii=False),
                "subtype_options": ", ".join(subtype_options) or "(없음)",
                "page_text": classified.pages_by_pkg[c["package"]][c["page"]],
            },
        )
        _apply_text_answer(c, parsed, r.type_name)


# ── [1b] VLM: pages with no text layer at all ─────────────────
def _resolve_image_pages_by_vlm(r: _Run, classified: _Classified
                                ) -> dict[tuple[str, int], dict]:
    """Returns what the model read off each image page, for the card stage.

    render_upright_png decides the rotation from the rendered pixels rather than
    from the stored /Rotate, which on these scans disagrees with the content
    (known_limits.md §5).
    """
    extracts: dict[tuple[str, int], dict] = {}
    for c in classified.rows:
        if c["grade"] != "DEFER_VLM" or c["package"] not in r.scope or r.llm is None:
            continue
        with pymupdf.open(r.packages[c["package"]][0]) as pdf:
            png, orientation = render_upright_png(pdf[c["page"]], VLM_DPI)
        c["render_orientation"] = orientation.to_dict()
        parsed = r.llm.complete_json_vision(
            stage="classify_page_vision",
            prompt_name="classify_page_vision",
            variables={
                "candidate_types": "\n".join(f"- {t}" for t in r.all_types),
                "package": c["package"],
                "page": str(c["page"]),
            },
            image_png=png,
        )
        c["llm"] = parsed
        if parsed.get("type") == r.type_name:
            c["type"], c["grade"] = r.type_name, "VLM"
            c["subtype"] = parsed.get("subtype")
            extracts[(c["package"], c["page"])] = parsed.get("extracted") or {}
        elif parsed.get("type") in (None, "UNRESOLVED"):
            c["grade"] = "VLM_UNRESOLVED"
        else:
            c["type"], c["grade"] = None, "VLM"
    return extracts


def _write_classifications(r: _Run, classified: _Classified) -> None:
    with (r.out_dir / "classification.jsonl").open("w", encoding="utf-8") as f:
        for c in classified.rows:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    n_typed = sum(1 for c in classified.rows if c["type"] == r.type_name)
    print(f"[1] 판정 완료: {len(classified.rows)}p 중 {r.type_name} {n_typed}p")


# ── [2] signal cards (in-scope pages of this type) ────────────
def _build_cards(r: _Run, classified: _Classified,
                 vlm_extracts: dict[tuple[str, int], dict]) -> dict[str, list]:
    cards_by_pkg: dict[str, list] = {}
    with (r.out_dir / "cards.jsonl").open("w", encoding="utf-8") as f:
        for pkg in r.scope:
            cards = []
            with pymupdf.open(r.packages[pkg][0]) as pdf:
                for c in classified.rows:
                    if c["package"] != pkg or c["type"] != r.type_name:
                        continue
                    card = build_card(
                        pkg, c["page"], classified.page_texts[(pkg, c["page"])],
                        classified.signal_results[(pkg, c["page"])], c["subtype"],
                        r.policy, pdf[c["page"]],
                    )
                    extracted = vlm_extracts.get((pkg, c["page"]))
                    if extracted:  # image page: the card is empty without this
                        apply_vlm_extract(card, extracted)
                    cards.append(card)
                    f.write(json.dumps(card.to_dict(), ensure_ascii=False) + "\n")
            cards_by_pkg[pkg] = cards
            print(f"[2] 신호 카드: pkg{pkg} {len(cards)}장")
    return cards_by_pkg


# ── [3][4] grouping + ordering ───────────────────────────────
def _group_and_order(r: _Run, classified: _Classified,
                     cards_by_pkg: dict[str, list]) -> tuple[dict, dict]:
    groupings: dict[str, dict] = {}
    orderings: dict[str, dict] = {}
    if r.llm is None:
        skipped = json.dumps({"status": "SKIPPED", "reason": "--no-llm"}, ensure_ascii=False)
        (r.out_dir / "grouping.json").write_text(skipped, encoding="utf-8")
        (r.out_dir / "ordering.json").write_text(skipped, encoding="utf-8")
        print("[3][4] SKIPPED (--no-llm)")
        return groupings, orderings

    for pkg in r.scope:
        if not cards_by_pkg[pkg]:
            print(f"[3][4] pkg{pkg}: 대상 페이지 없음 — 건너뜀")
            continue
        g = group_pages(pkg, cards_by_pkg[pkg], classified.pages_by_pkg[pkg], r.policy, r.llm)
        groupings[pkg] = g
        orderings[pkg] = order_instances(g, cards_by_pkg[pkg], r.policy)
        print(f"[3][4] pkg{pkg}: instance {len(g.get('instances', []))}개, "
              f"unresolved {len(g.get('unresolved_pages', []))}p")
    (r.out_dir / "grouping.json").write_text(
        json.dumps(groupings, ensure_ascii=False, indent=2), encoding="utf-8")
    (r.out_dir / "ordering.json").write_text(
        json.dumps(orderings, ensure_ascii=False, indent=2), encoding="utf-8")
    return groupings, orderings


# ── GT + checks ──────────────────────────────────────────────
def _verify_and_report(r: _Run, args: argparse.Namespace, check_prefix: str,
                       classified: _Classified, cards_by_pkg: dict[str, list],
                       groupings: dict, orderings: dict) -> None:
    rows = classified.rows
    # Answer-key files are recognized the same way the unified CLI recognizes
    # them, so the two paths never disagree about what the originals are.
    answer_keys = {f.path.name: f.doc_type for f in discover_inputs(args.data_dir).answer_keys}
    gt_rows, gt_coverage = build_ground_truth(
        answer_keys, r.parsed_dir, r.packages[r.gt_label][1],
        args.out_dir / "ground_truth" / f"pkg{r.gt_label}.jsonl",
    )
    if gt_coverage < 1.0:
        print(f"⚠️  패키지 {r.gt_label} 의 정답 매칭률이 {gt_coverage:.0%} 입니다 — 검증이 부분적입니다.")
    expected, warnings = load_expected_pages(r.type_name, sorted(r.packages))
    for w in warnings:
        print(f"⚠️  {w}")

    verify_cfg = r.policy.get("verification", {})
    results = run_verifications(
        r.type_name, rows, groupings, orderings,
        gt_rows, gt_label=r.gt_label, expected_pages=expected, prefix=check_prefix,
        universal_only=(classified.universal_only.get(r.gt_label)
                        if r.policy.get("vendors") else None),
        gt_exclude_source_pages=verify_cfg.get("gt_exclude_source_pages"),
        instance_expectations=verify_cfg.get("instance_expectations"),
        require_final_type=verify_cfg.get("require_final_type", False),
        markers_by_page={
            pkg: {c.page: [(m["n"], m["y"]) for m in c.page_marker_candidates] for c in cards}
            for pkg, cards in cards_by_pkg.items()
        },
    )

    report = render_report(
        r.type_name, results, groupings.get(r.gt_label), orderings.get(r.gt_label),
        r.llm.this_run if r.llm else None, args.no_llm,
        layers=layer_contribution(rows, r.type_name),
        subtype_counts=dict(Counter(f"{c['package']}:{c['subtype']}" for c in rows
                                    if c["type"] == r.type_name)),
        conflicts=[
            {"package": c["package"], "page": c["page"], "types": c["flags"]["type_conflict"]}
            for c in rows if c["flags"].get("type_conflict")
        ],
        warnings=warnings,
        excluded_pages=_excluded_pages(rows, gt_rows, r, verify_cfg),
        vlm_pages=_vlm_pages(rows),
    )
    (r.out_dir / "report.md").write_text(report, encoding="utf-8")
    for res in results:
        verdict = "MEASURE" if res.measurement is not None else ("PASS" if res.passed else "FAIL")
        print(f"{res.name}: {verdict} — {res.detail}")
    print(f"report: {r.out_dir / 'report.md'}")


def _excluded_pages(rows: list[dict], gt_rows: list[dict], r: _Run,
                    verify_cfg: dict) -> list[dict] | None:
    """Pages the policy excludes from the checks, reported separately.

    None means the policy excludes nothing, which the report renders
    differently from "excludes something, and here it is".
    """
    excluded_src = set(verify_cfg.get("gt_exclude_source_pages") or [])
    if not excluded_src:
        return None
    excluded_input = {
        row["input_page"] for row in gt_rows
        if row["document_type"] == r.type_name and row["source_page"] in excluded_src
    }
    return [c for c in rows
            if c["package"] == r.gt_label and c["page"] in excluded_input]


def _vlm_pages(rows: list[dict]) -> list[dict] | None:
    """Image pages and their outcome. None when this run had none at all."""
    if not any(c["grade"] == "DEFER_VLM" or c["grade"].startswith("VLM") for c in rows):
        return None
    return [c for c in rows if c["grade"].startswith("VLM")
            or (c.get("llm") and c["grade"] == "DEFER_VLM")]
