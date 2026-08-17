"""``docsplit run`` — the whole thing, one command.

    uv run docsplit run

Reads whatever PDFs are in data/, classifies every page, groups pages back into
documents, and writes results/. Intermediate artifacts (including page text)
land in outputs/, which is gitignored; results/ is content-free by design.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import pymupdf

from .rules.cards import apply_vlm_extract, build_card
from .ingest.discover import discover_inputs
from .llm.grouping import group_pages, order_instances
from .output.ground_truth import build_ground_truth
from .llm.client import DEFAULT_MODEL, LLMClient, LLMDisabled
from .ingest.parse import export_inspection, export_jsonl
from .ingest.pdf_parser import parse_pdf, render_page_png
from .output.results import (
    score_against_gt,
    write_classification_csv,
    write_documents_json,
    write_evaluation_md,
    write_summary_md,
)
from .rules.signals import available_policies, evaluate_signals, load_policy
from .rules.unified import (
    OTHER_TYPE,
    apply_llm_answer,
    classify_page_unified,
    llm_variables,
)

VLM_DPI = 150  # 스캔 꼬리말(폼 코드·페이지 마커)까지 읽히는 해상도

# Published per-1M-token prices for the default model, used only to turn the
# measured token counts into a cost figure in the summary.
# Source: developers.openai.com/api/docs/pricing, 확인 2026-08-17 (standard tier).
PRICE_PER_1M = {"input": 0.75, "output": 4.50}


def _step(n: int, text: str) -> None:
    print(f"[{n}/8] {text}", flush=True)


def _usd(usage: dict) -> float:
    prompt = sum(u["prompt_tokens"] for u in usage.values())
    completion = sum(u["completion_tokens"] for u in usage.values())
    return prompt / 1e6 * PRICE_PER_1M["input"] + completion / 1e6 * PRICE_PER_1M["output"]


def _cost(usage: dict, usage_path: Path) -> dict:
    """This run's cost, plus everything spent on this cache to date.

    The cumulative figure is the honest answer to "what did this cost to
    build" — a cached re-run reports zero, which is true but not the number a
    reader wants.
    """
    cumulative = {}
    if usage_path.exists():
        cumulative = json.loads(usage_path.read_text(encoding="utf-8")).get("cumulative", {})
    return {
        "model": DEFAULT_MODEL,
        "input_per_1m": PRICE_PER_1M["input"],
        "output_per_1m": PRICE_PER_1M["output"],
        "total_usd": _usd(usage),
        "cumulative_usd": _usd(cumulative) if cumulative else None,
        "cumulative_calls": sum(u["calls"] for u in cumulative.values()) if cumulative else None,
    }


def run(args: argparse.Namespace) -> int:
    # ── [1] what did the user give us ─────────────────────────
    _step(1, f"입력 파일 인식 ({args.data_dir}/)")
    discovery = discover_inputs(args.data_dir)
    print(discovery.render_table())
    for w in discovery.warnings:
        print(f"  ⚠️  {w}")

    policies = {}
    for name in available_policies():
        policy = load_policy(name)
        policies[policy["type"]] = policy
    known_types = set(policies)
    subtype_options = sorted(
        {
            name
            for policy in policies.values()
            for vblock in (policy.get("vendors") or {}).values()
            for name in (vblock.get("subtypes") or {})
        }
        | {
            name
            for policy in policies.values()
            for name in (policy.get("subtypes", {}).get("suffix_map") or {}).values()
        }
    )
    print(f"       정책 {len(policies)}종: {', '.join(sorted(policies))} (+{OTHER_TYPE}는 정책 없음)")

    # ── [2] text extraction ───────────────────────────────────
    _step(2, "PDF 텍스트 추출")
    parsed_dir = args.out_dir / "parsed"
    pages_by_pkg: dict[str, dict[int, str]] = {}
    for f in discovery.all_files():
        records = parse_pdf(f.path)
        export_jsonl(records, parsed_dir / f"{f.slug}.jsonl")
        export_inspection(records, args.out_dir / "inspection" / f.slug)
        if f.role == "package":
            pages_by_pkg[f.label] = {r.page_index: r.raw_text for r in records}
            print(f"       패키지 {f.label}: {len(records)}p")

    # ── [3] rule classification, all policies at once ─────────
    _step(3, "규칙 분류 (4개 정책 동시 평가)")
    verdicts: dict[str, list] = {}
    page_texts: dict[tuple[str, int], object] = {}
    for label, pages in sorted(pages_by_pkg.items()):
        vs = []
        for page_index, raw in sorted(pages.items()):
            v, ptext, _ = classify_page_unified(label, page_index, raw, policies)
            page_texts[(label, page_index)] = ptext
            vs.append(v)
        verdicts[label] = vs
        settled = sum(1 for v in vs if v.type)
        print(f"       패키지 {label}: 규칙 확정 {settled}p / 판단 보류 {len(vs) - settled}p")

    # ── LLM client (optional) ─────────────────────────────────
    llm = None
    if not args.no_llm:
        try:
            llm = LLMClient(cache_dir=args.out_dir / "llm_cache",
                            usage_path=args.out_dir / "llm_usage.json")
        except LLMDisabled:
            print("  ⚠️  OPENAI_API_KEY가 없어 LLM 단계를 건너뜁니다.\n"
                  "      규칙으로 확정되지 않은 페이지는 미판정으로 남습니다.\n"
                  "      키를 넣고 다시 실행하거나, 의도한 것이라면 --no-llm 으로 실행하세요.")

    # ── [4] LLM for pages the rules could not settle ──────────
    need_llm = [(lb, v) for lb, vs in verdicts.items() for v in vs
                if v.rule_grade == "DEFER_LLM"]
    _step(4, f"LLM 분류 {len(need_llm)}건" + (" (건너뜀)" if llm is None else ""))
    if llm is not None:
        for label, v in need_llm:
            parsed = llm.complete_json(
                stage="classify_page",
                prompt_name="classify_page",
                variables=llm_variables(v, pages_by_pkg[label][v.page], subtype_options),
            )
            apply_llm_answer(v, parsed, known_types)

    # ── [5] VLM for pages with no text layer ──────────────────
    need_vlm = [(lb, v) for lb, vs in verdicts.items() for v in vs
                if v.rule_grade == "DEFER_VLM"]
    _step(5, f"VLM 분류 {len(need_vlm)}건" + (" (건너뜀)" if llm is None else ""))
    vlm_extracts: dict[tuple[str, int], dict] = {}
    pdf_by_label = {f.label: f.path for f in discovery.packages}
    if llm is not None and need_vlm:
        for label, v in need_vlm:
            with pymupdf.open(pdf_by_label[label]) as pdf:
                png = render_page_png(pdf[v.page], VLM_DPI)
            parsed = llm.complete_json_vision(
                stage="classify_page_vision",
                prompt_name="classify_page_vision",
                variables={
                    "candidate_types": "\n".join(f"- {t}" for t in [*sorted(known_types), OTHER_TYPE]),
                    "package": label,
                    "page": str(v.page),
                },
                image_png=png,
            )
            apply_llm_answer(v, parsed, known_types)
            if v.type in known_types:
                vlm_extracts[(label, v.page)] = parsed.get("extracted") or {}

    # ── [6] grouping + [7] ordering, per type ─────────────────
    _step(6, "문서 그룹핑")
    groupings: dict[str, dict] = defaultdict(dict)
    orderings: dict[str, dict] = defaultdict(dict)
    cards_by_pkg_type: dict[tuple[str, str], list] = {}
    for label, vs in sorted(verdicts.items()):
        pdf = pymupdf.open(pdf_by_label[label])
        for type_name, policy in sorted(policies.items()):
            typed = [v for v in vs if v.type == type_name]
            if not typed:
                continue
            cards = []
            for v in typed:
                res = evaluate_signals(page_texts[(label, v.page)], policy)
                card = build_card(label, v.page, page_texts[(label, v.page)],
                                  res, v.subtype, policy, pdf[v.page])
                extracted = vlm_extracts.get((label, v.page))
                if extracted:
                    apply_vlm_extract(card, extracted)
                cards.append(card)
            cards_by_pkg_type[(label, type_name)] = cards
            if llm is None:
                continue
            g = group_pages(label, cards, pages_by_pkg[label], policy, llm)
            groupings[label][type_name] = g
            orderings[label][type_name] = order_instances(g, cards, policy)
        pdf.close()
        made = sum(len(g.get("instances", [])) for g in groupings.get(label, {}).values())
        print(f"       패키지 {label}: instance {made}개")

    _step(7, "순서 복원")
    for label in sorted(orderings):
        methods = [i.get("method") for o in orderings[label].values()
                   for i in o.get("instances", [])]
        print(f"       패키지 {label}: {', '.join(sorted(set(m for m in methods if m))) or '—'}")

    # ── [8] results ───────────────────────────────────────────
    _step(8, f"결과 저장 ({args.results_dir}/)")
    answer_keys = {f.path.name: f.doc_type for f in discovery.answer_keys}
    usage = llm.this_run if llm else None
    for label, vs in sorted(verdicts.items()):
        out_dir = args.results_dir / f"package_{label}"
        rows = [v.to_dict() for v in vs]
        write_classification_csv(rows, out_dir / "classification.csv")
        write_documents_json(groupings.get(label, {}), orderings.get(label, {}),
                             out_dir / "documents.json")

        gt_rows, coverage = build_ground_truth(
            answer_keys, parsed_dir, parsed_dir / f"{_slug_for(discovery, label)}.jsonl",
            args.out_dir / "ground_truth" / f"pkg{label}.jsonl",
        )
        scored = None
        if coverage == 1.0 and gt_rows:
            scored = score_against_gt(rows, gt_rows)
            write_evaluation_md(label, scored, groupings.get(label, {}),
                                orderings.get(label, {}), gt_rows,
                                out_dir / "evaluation.md")
            print(f"       패키지 {label}: 정답 대조 완료 "
                  f"(accuracy {scored['accuracy']:.3f}) → {out_dir}/evaluation.md")
        else:
            print(f"       패키지 {label}: 정답 원본 없음 — 분류 결과만 산출 "
                  f"(정답 매칭률 {coverage:.0%})")
        write_summary_md(label, rows, groupings.get(label, {}), orderings.get(label, {}),
                         scored, usage, _cost(usage, args.out_dir / 'llm_usage.json') if usage else None,
                         out_dir / "summary.md")

    # full detail, including evidence text, stays out of results/
    (args.out_dir / "unified_classification.jsonl").write_text(
        "\n".join(json.dumps(v.to_dict(), ensure_ascii=False)
                  for vs in verdicts.values() for v in vs) + "\n",
        encoding="utf-8",
    )
    print(f"\n완료. 최종 결과: {args.results_dir}/  중간 산출물: {args.out_dir}/")
    return 0


def _slug_for(discovery, label: str) -> str:
    for f in discovery.packages:
        if f.label == label:
            return f.slug
    raise KeyError(label)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="docsplit", description=__doc__)
    sub = ap.add_subparsers(dest="command")
    run_p = sub.add_parser("run", help="전체 파이프라인 실행")
    run_p.add_argument("--data-dir", type=Path, default=Path("data"))
    run_p.add_argument("--out-dir", type=Path, default=Path("outputs"))
    run_p.add_argument("--results-dir", type=Path, default=Path("results"))
    run_p.add_argument("--no-llm", action="store_true",
                       help="규칙 판정까지만 수행 (API 키 불필요)")
    args = ap.parse_args(argv)
    if args.command != "run":
        ap.print_help()
        return 1
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
