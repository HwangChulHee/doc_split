"""One-off: compare dataset credit-report pages against Xactus vendor guides.

Vendor guides are product documentation, not a normative standard, so a match
here is "vendor-document verified" — a weaker grade than the GSE-blank
evidence used for URLA. This script only reports; it decides nothing.

Outputs (outputs/credit_vendor_diff/):
  guide_phrases.txt        phrase inventory harvested from the guides
  form_fit.txt             per-form marker presence in the dataset
  page_<pkg>_<n>.txt       per-page line classification
  vendor_phrase_pages.txt  guide phrase -> dataset pages containing it
  dataset_only.txt         dataset lines with no guide counterpart

Usage:
  uv run python scripts/observe_credit_diff.py --out-dir outputs/credit_vendor_diff
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import pymupdf

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
from docsplit.rules.normalize import PageText, match_phrase, normalize  # noqa: E402

GUIDE_DIR = REPO / "data/reference/credit/xactus"
FORM_GUIDES = {
    "Form 1": "credit_report_reference_guide_form_1.pdf",
    "Form 2": "credit_report_reference_guide_form_2.pdf",
    "Form 3": "credit_report_reference_guide_form_3.pdf",
}
# File names carry loan numbers, so they are discovered rather than hardcoded
# (same convention as src/docsplit/urla_pipeline.py).
PKG01_CREDIT_GLOB = "Credit_Report*.jsonl"
PACKAGE_GLOB = "*_shuffled.jsonl"
PKG02_CREDIT_PAGES = [1, 3, 5, 7, 9, 13, 18, 20, 23, 27, 31, 33, 37, 40, 43]

# Markers that differ between the three documented layouts (guide legend items)
FORM_MARKERS = {
    "Form 1": ["Credit Summary", "FICO Scores", "Maximum Delinquency", "Manner of Payment",
               "Months Reviewed", "Reported On", "Red Asterisk"],
    "Form 2": ["File Summary", "Whose", "Repository Files Returned", "Creditors",
               "Credit Score Information", "Notice to Home Loan Applicant"],
    "Form 3": ["Report Summary", "Extensive borrower information", "Collections",
               "Disputed Account", "Footnotes", "Open Date"],
}

# Legal / quasi-standard notices worth enumerating separately (phrase -> label)
LEGAL_PROBES = {
    "section 326 of the Patriot Act": "patriot_act_ofac",
    "Office of Foreign Asset Control": "ofac_named",
    "Merged Mortgage Credit Report": "mmcr_certification",
    "FACT Act": "fact_act",
    "Fair and Accurate Credit Transactions Act": "fact_act_full",
    "THE REPORTING BUREAU CERTIFIES THAT": "repository_certification",
    "Legislative Cost Recovery Fees": "cost_recovery_fees",
    "Consumer Financial Protection Bureau": "cfpb",
    "End of Report": "end_of_report",
    "Notice to Home Loan Applicant": "score_disclosure_notice",
    "In compliance with": "compliance_preamble",
}

# Header elements observed in the dataset -> guide legend item they map to
HEADER_PROBES = {
    "Report ID:": "item 4 (Report ID number)",
    "Repositories:": "item 4 (Repositories)",
    "Price:": "item 4 (Price)",
    "Order Verifications": "item 5",
    "Loan Number:": "item 2 (Loan Number)",
    "Requested By:": "item 2 (Requested By)",
    "Client Code:": "item 2 (Customer Code) — 라벨 표기 상이",
    "Customer Code": "item 2 원문 표기 (데이터셋 대조용)",
    "Date Ordered": "item 3 원문 표기 (데이터셋 대조용)",
    "Date Released": "item 3 원문 표기 (데이터셋 대조용)",
    "Ordered:": "item 3 (Date Ordered)",
    "Released:": "item 3 (Date Released/Completed)",
    "Reissued:": "item 3 (Date Reissued)",
    "Originally Requested By:": "(가이드 미언급 후보)",
}

# Tradeline field labels documented in the Form 1 legend / sample
TRADELINE_FIELDS = [
    "Account Number", "ECOA", "Opened", "Last Activity", "Closed", "Reported",
    "Credit Limit", "High Credit", "Past Due", "Payment", "Balance",
    "Account Type", "Collateral", "Terms", "Reported On", "Manner of Payment",
    "Months Reviewed", "30-59 Days Late", "60-89 Days Late", "90-119 Days Late",
    "120-149 Days Late", "150+ Days Late", "Comment", "Scheduled", "Actual",
    "Trended Data", "Individual", "Joint",
]

VALUE_RE = re.compile(r"^[\d\s$,.:%()/*+-]*$")
DATE_RE = re.compile(r"^\d{1,2}/\d{1,2}/\d{2,4}$|^\d{2}/\d{4}$")


def guide_text() -> dict[str, PageText]:
    out = {}
    for label, fname in FORM_GUIDES.items():
        with pymupdf.open(GUIDE_DIR / fname) as doc:
            raw = "\n".join(pg.get_text() for pg in doc)
        out[label] = PageText.from_raw(raw)
    return out


def harvest_guide_phrases(guides: dict[str, PageText]) -> dict[str, list[str]]:
    """Lines from the guides that look like labels/notices, keyed by form."""
    phrases: dict[str, list[str]] = {}
    for label, gt in guides.items():
        keep = []
        for ln in gt.lines:
            if len(ln) < 3 or VALUE_RE.fullmatch(ln) or DATE_RE.fullmatch(ln):
                continue
            keep.append(ln)
        phrases[label] = sorted(set(keep))
    return phrases


def dataset_pages() -> list[tuple[str, int, str]]:
    """pkg01: the standalone credit-report original. pkg02: credit pages of the 2nd package."""
    parsed = REPO / "outputs/parsed"
    credit01 = next(iter(sorted(parsed.glob(PKG01_CREDIT_GLOB))), None)
    packages = sorted(parsed.glob(PACKAGE_GLOB))
    if credit01 is None or len(packages) < 2:
        raise SystemExit(
            f"{parsed} 에서 대상 파일을 찾지 못했습니다 — 먼저 파싱을 실행하세요: "
            "uv run python -m docsplit.ingest.parse"
        )
    out = []
    for rec in (json.loads(l) for l in credit01.open(encoding="utf-8")):
        out.append(("pkg01", rec["page_index"], rec["raw_text"]))
    for rec in (json.loads(l) for l in packages[1].open(encoding="utf-8")):
        if rec["page_index"] in PKG02_CREDIT_PAGES:
            out.append(("pkg02", rec["page_index"], rec["raw_text"]))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=Path, default=REPO / "outputs/credit_vendor_diff")
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    guides = guide_text()
    phrases = harvest_guide_phrases(guides)
    all_guide_lines = {ln for lst in phrases.values() for ln in lst}
    guide_fulltext = {k: v.fulltext for k, v in guides.items()}

    (args.out_dir / "guide_phrases.txt").write_text(
        "\n".join(f"[{form}] {ln}" for form, lst in phrases.items() for ln in lst),
        encoding="utf-8",
    )

    pages = dataset_pages()
    page_objs = {(pkg, n): PageText.from_raw(txt) for pkg, n, txt in pages}

    # ── form fit ──────────────────────────────────────────────
    fit_lines = ["# Form marker presence in dataset", ""]
    for form, markers in FORM_MARKERS.items():
        fit_lines.append(f"## {form}")
        for m in markers:
            in_guide = normalize(m) in guide_fulltext[form]
            hits = sorted(
                f"{pkg}:p{n}" for (pkg, n), po in page_objs.items() if match_phrase(m, po)
            )
            fit_lines.append(f"  {m!r:34} guide={in_guide} dataset={len(hits)}p {hits[:8]}")
        fit_lines.append("")
    (args.out_dir / "form_fit.txt").write_text("\n".join(fit_lines), encoding="utf-8")

    # ── probes: header / legal / tradeline ────────────────────
    probe_lines = ["# Probe results (phrase -> dataset pages)", ""]
    for title, probes in (
        ("HEADER", HEADER_PROBES), ("LEGAL", LEGAL_PROBES),
        ("TRADELINE", {f: "" for f in TRADELINE_FIELDS}),
    ):
        probe_lines.append(f"## {title}")
        for phrase, note in probes.items():
            in_guides = [f for f, ft in guide_fulltext.items() if normalize(phrase) in ft]
            p1 = sorted(n for (pkg, n), po in page_objs.items() if pkg == "pkg01" and match_phrase(phrase, po))
            p2 = sorted(n for (pkg, n), po in page_objs.items() if pkg == "pkg02" and match_phrase(phrase, po))
            probe_lines.append(
                f"  {phrase!r:36} guides={in_guides} pkg01={p1} pkg02={p2}" + (f"  # {note}" if note else "")
            )
        probe_lines.append("")
    (args.out_dir / "vendor_phrase_pages.txt").write_text("\n".join(probe_lines), encoding="utf-8")

    # ── per-page line classification ─────────────────────────
    dataset_only: dict[str, list[str]] = defaultdict(list)
    for pkg, n, raw in pages:
        po = page_objs[(pkg, n)]
        rows, counts = [], defaultdict(int)
        for ln in po.lines:
            if ln in all_guide_lines:
                cls = "VENDOR_DOC"
            elif any(ln in ft for ft in guide_fulltext.values()) and len(ln) >= 8:
                cls = "VENDOR_DOC~"
            elif VALUE_RE.fullmatch(ln) or DATE_RE.fullmatch(ln):
                cls = "FILLED?"
            else:
                cls = "UNMATCHED"
                dataset_only[ln].append(f"{pkg}:p{n}")
            counts[cls] += 1
            rows.append(f"[{cls:11}] {ln[:110]}")
        (args.out_dir / f"page_{pkg}_{n:03d}.txt").write_text(
            f"# {pkg} p{n} {dict(counts)}\n" + "\n".join(rows) + "\n", encoding="utf-8"
        )

    with (args.out_dir / "dataset_only.txt").open("w", encoding="utf-8") as f:
        for ln, pgs in sorted(dataset_only.items(), key=lambda kv: -len(kv[1])):
            f.write(f"[{len(pgs):3}x {','.join(sorted(set(pgs))[:6])}] {ln[:120]}\n")

    print(f"guide phrases: {sum(len(v) for v in phrases.values())} ({len(all_guide_lines)} distinct)")
    print(f"dataset pages: {len(pages)} (pkg01 {sum(1 for p in pages if p[0]=='pkg01')}, "
          f"pkg02 {sum(1 for p in pages if p[0]=='pkg02')})")
    print(f"distinct unmatched dataset lines: {len(dataset_only)}")
    print(f"-> {args.out_dir}")


if __name__ == "__main__":
    main()
