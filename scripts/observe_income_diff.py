"""One-off: compare dataset income pages against IRS references and vendor samples.

INCOME is the widest and least standardized of the four types, and the dataset
holds only seven pages of it. A signal fitted to those seven will not survive
contact with the next package, so every probe here is tagged with **why it
would hold outside this dataset**:

  IRS_STANDARD    the label comes from an IRS product (transcript / form blank)
  VENDOR_OVERLAY  a delivery vendor stamped it on; no IRS counterpart
  FILLED          a value
  UNCERTAIN       no reference either way

The reference for transcripts is NASFAA's Tax Transcript Decoder, which prints
annotated IRS transcript samples (Tax Return Transcript and Wage & Income
Transcript). It is an industry publication reproducing IRS output, not an IRS
publication — a weaker grade than the form blanks, which come from irs.gov.

This script only reports; it decides nothing.

Outputs (outputs/income_standard_diff/):
  transcript_skeleton.txt  common transcript header/footer across types
  vendor_overlay.txt       which dataset labels have no IRS counterpart
  page_<pkg>_<n>.txt       per-page line classification
  pairing.txt              materials for pairing the two transcript copies
  twn.txt                  TWN sample labels vs the dataset page
  corelogic.txt            the verification-vendor page, observation only
  pl_probe.txt             P&L vocabulary probe over the P&L page
  cross_contamination.txt  income vocabulary hits on pages of other types
  unobserved_vocab.txt     identifiers harvested from IRS blanks (未觀察 대비)

Usage:
  uv run python scripts/observe_income_diff.py --out-dir outputs/income_standard_diff
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import pymupdf
import yaml

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
from docsplit.normalize import PageText, match_phrase, normalize  # noqa: E402

REF = REPO / "data/reference/income"
NASFAA = REF / "irs/transcripts/nasfaa_tax_transcript_decoder.pdf"
# TWN sample already lives under the credit reference tree; not duplicated here.
TWN_SAMPLE = REPO / "data/reference/credit/xactus/twn_indicator_sample.pdf"
IRS_TYPES = REF / "irs/transcript_types.html"
FANNIE_PL = REF / "vendors/fannie_b3-3.7-04_pl_statements.html"
FORM_BLANKS = {
    "W-2": "fw2.pdf",
    "1040": "f1040.pdf",
    "4506-C": "f4506c.pdf",
    "1099-MISC": "f1099msc.pdf",
    "1099-NEC": "f1099nec.pdf",
}

# NASFAA pages holding transcript samples (surveyed by hand; see SOURCES.md)
NASFAA_WI_PAGES = [16]        # Wage and Income Transcript
NASFAA_TRT_PAGES = [8, 9, 10, 11, 12]  # Tax Return Transcript (multi-page)

# File names carry loan numbers, so they are discovered rather than hardcoded.
PKG01_INCOME_GLOB = "INCOME*.jsonl"
PACKAGE_GLOB = "*_shuffled.jsonl"
PKG02_INCOME_PAGES = {
    11: "irs_transcript",
    26: "irs_transcript",
    30: "irs_transcript",
    38: "irs_transcript",
    31: "twn",
    35: "corelogic",
}

# ── probes ───────────────────────────────────────────────────
# The transcript family skeleton: labels expected on every IRS transcript
# regardless of which type it is.
SKELETON = [
    "This Product Contains Sensitive Taxpayer Data",
    "Internal Revenue Service",
    "United States Department of the Treasury",
    "Request Date:",
    "Response Date:",
    "Tracking Number:",
    "Customer File Number:",
    "SSN Provided:",
    "TIN Provided:",
    "Tax Period Ending:",
    "Tax Period Requested:",
]

TRANSCRIPT_TITLES = [
    "Wage and Income Transcript",
    "Tax Return Transcript",
    "Tax Account Transcript",
    "Record of Account Transcript",
    "Verification of Non-filing Letter",
]

# W-2 block labels as the transcript prints them (not as the W-2 form prints them)
W2_BLOCK = [
    "Form W-2 Wage and Tax Statement",
    "Employer:",
    "Employer Identification Number (EIN):",
    "Employee:",
    "Employee's Social Security Number:",
    "Submission Type:",
    "Wages, Tips and Other Compensation:",
    "Federal Income Tax Withheld:",
    "Social Security Wages:",
    "Social Security Tax Withheld:",
    "Medicare Wages and Tips:",
    "Medicare Tax Withheld:",
    "Deferred Compensation:",
    'Code "DD" Cost of Employer-Sponsored Health Coverage:',
    'Code "W" Employer Contributions to a Health Savings Account:',
    "Third Party Sick Pay Indicator:",
    "Retirement Plan Indicator:",
    "Statutory Employee:",
    "W2 Submission Type:",
    "W2 WHC SSN Validation Code:",
    "Original document",
]

# Labels seen in the dataset that may be vendor stamps rather than IRS output
OVERLAY_CANDIDATES = [
    "Ref:",
    "Report ID:",
    "File Number:",
    "Loan Number:",
    "PREPARED FOR:",
    "PREPARED BY:",
    "Account:",
    "IRS Form Types:",
    "Years:",
    "Income Summary",
    "Received:",
    "Completed:",
]

TWN_LABELS = [
    "The Work Number",
    "Employment Record Available",
    "Client Name:",
    "Ordered:",
    "Address:",
    "Address 2:",
    "City, State, Zip:",
    "Report ID:",
    "Loan Number:",
    "Borrower:",
    "Co-Borrower:",
    "SSN:",
    "Requested By:",
    "End of Report",
    "Experian",
    "consumer reporting agency",
]

# What a typical P&L would carry (Fannie B3-3.7-04: "similar to Schedule C")
PL_VOCAB = [
    "Profit and Loss", "Profit & Loss", "P&L", "Income Statement",
    "Revenue", "Revenues", "Gross Receipts", "Sales", "Gross Income",
    "Expenses", "Total Expenses", "Operating Expenses", "Cost of Goods Sold",
    "Net Income", "Net Profit", "Net Loss", "Net Earnings",
    "Year to Date", "YTD", "For the period", "Advertising", "Insurance",
    "Legal and professional services", "Office expense", "Rent",
    "Supplies", "Travel", "Utilities", "Depreciation", "Commissions and fees",
    "Car and truck expenses", "Meals",
]

# Income words at risk of firing on other document types
CONTAMINATION_PROBES = [
    "Wages", "Income", "Employer", "Employee", "W-2", "Salary",
    "Employment", "Gross Income", "Tax Return", "Social Security",
    "Medicare", "Withheld", "Tax Period", "Self Employed", "Base Income",
    "Overtime", "Bonus", "Taxpayer",
]


def html_text(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    raw = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
    return html.unescape(re.sub(r"(?is)<[^>]+>", "\n", raw))


def pdf_pages(path: Path) -> list[str]:
    with pymupdf.open(path) as doc:
        return [p.get_text() for p in doc]


def mask(text: str) -> str:
    """Digits out; the shape of a line is enough for this report."""
    return re.sub(r"\d", "#", text)[:120]


def dataset_pages() -> tuple[list[tuple[str, int, str]], dict]:
    """Income pages under study, plus every page keyed by (pkg, page) for §4-6."""
    parsed = REPO / "outputs/parsed"
    income01 = next(iter(sorted(parsed.glob(PKG01_INCOME_GLOB))), None)
    packages = sorted(parsed.glob(PACKAGE_GLOB))
    if income01 is None or len(packages) < 2:
        raise SystemExit(
            f"{parsed} 에서 대상 파일을 찾지 못했습니다 — 먼저 파싱을 실행하세요: "
            "uv run python -m docsplit.parse"
        )
    studied: list[tuple[str, int, str]] = []
    for rec in (json.loads(l) for l in income01.open(encoding="utf-8")):
        studied.append(("pkg01_income", rec["page_index"], rec["raw_text"]))
    every: dict[tuple[str, int], str] = {}
    for label, path in zip(("pkg01", "pkg02"), packages):
        for rec in (json.loads(l) for l in path.open(encoding="utf-8")):
            every[(label, rec["page_index"])] = rec["raw_text"]
            if label == "pkg02" and rec["page_index"] in PKG02_INCOME_PAGES:
                studied.append(("pkg02", rec["page_index"], rec["raw_text"]))
    return studied, every


def type_map() -> dict[tuple[str, int], str]:
    """(pkg, page) -> document type, for the cross-contamination measurement.

    pkg01 comes from the generated ground truth; pkg02 has no answer key, so it
    uses the expected-page config plus this script's income list. Pages listed
    nowhere are recorded as UNKNOWN rather than silently counted as a negative.
    """
    out: dict[tuple[str, int], str] = {}
    gt = REPO / "outputs/ground_truth/pkg01.jsonl"
    if gt.exists():
        for rec in (json.loads(l) for l in gt.open(encoding="utf-8")):
            out[("pkg01", rec["input_page"])] = rec["document_type"]
    cfg_path = REPO / "config/expected_pages.yaml"
    if cfg_path.exists():
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        for type_name, per_label in cfg.items():
            for page in (per_label.get("02") or {}).get("expected", []):
                out[("pkg02", page)] = type_name
            for page in (per_label.get("02") or {}).get("expected_vlm", []):
                out[("pkg02", page)] = type_name
    for page in PKG02_INCOME_PAGES:
        out[("pkg02", page)] = "INCOME_DOC"
    return out


def probe_table(title: str, probes: list[str], refs: dict[str, PageText],
                pages: dict[tuple[str, int], PageText]) -> list[str]:
    rows = [f"## {title}", ""]
    for phrase in probes:
        present = [name for name, po in refs.items() if match_phrase(phrase, po)]
        hits = sorted(f"{pkg}:p{n}" for (pkg, n), po in pages.items()
                      if match_phrase(phrase, po))
        rows.append(f"  {phrase!r:60} 준거={present or '없음'} 데이터셋={len(hits)}p {hits}")
    rows.append("")
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=Path, default=REPO / "outputs/income_standard_diff")
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    nasfaa = pdf_pages(NASFAA)
    refs = {
        "NASFAA_W&I": PageText.from_raw("\n".join(nasfaa[i] for i in NASFAA_WI_PAGES)),
        "NASFAA_TRT": PageText.from_raw("\n".join(nasfaa[i] for i in NASFAA_TRT_PAGES)),
        "IRS_types": PageText.from_raw(html_text(IRS_TYPES)),
        "TWN_sample": PageText.from_raw("\n".join(pdf_pages(TWN_SAMPLE))),
        "Fannie_P&L": PageText.from_raw(html_text(FANNIE_PL)),
    }
    blanks = {
        name: PageText.from_raw("\n".join(pdf_pages(REF / "irs/forms" / fn)))
        for name, fn in FORM_BLANKS.items()
    }

    studied, every = dataset_pages()
    studied_objs = {(pkg, n): PageText.from_raw(t) for pkg, n, t in studied}
    transcript_objs = {k: v for k, v in studied_objs.items()
                       if k[0] == "pkg02" and PKG02_INCOME_PAGES.get(k[1]) == "irs_transcript"}

    # ── 1. transcript family skeleton ────────────────────────
    lines = ["# IRS transcript 공통 골격", "",
             "준거: NASFAA Tax Transcript Decoder의 두 샘플 (Wage&Income / Tax Return)", ""]
    lines += probe_table("공통 헤더·푸터 라벨", SKELETON, refs, transcript_objs)
    lines += probe_table("transcript 종류 명칭", TRANSCRIPT_TITLES, refs, studied_objs)
    lines += probe_table("W-2 블록 라벨 (transcript 표기)", W2_BLOCK, refs, transcript_objs)

    # sandwich: does the notice appear at both ends?
    lines += ["## 샌드위치 확인 — 고지문이 문서 상·하단 양쪽에 있는가", ""]
    notice = normalize("This Product Contains Sensitive Taxpayer Data")
    for name, page_idx in (("NASFAA_W&I", NASFAA_WI_PAGES), ("NASFAA_TRT", NASFAA_TRT_PAGES)):
        for i in page_idx:
            ls = [normalize(l) for l in nasfaa[i].splitlines() if l.strip()]
            pos = [j for j, l in enumerate(ls) if notice in l]
            where = [("상단" if j < len(ls) * 0.2 else "하단" if j > len(ls) * 0.8 else "중간")
                     for j in pos]
            if pos:
                lines.append(f"  {name} 원본 p{i}: {len(ls)}줄 중 {pos} → {where}")
    for (pkg, n), po in sorted(transcript_objs.items()):
        pos = [j for j, l in enumerate(po.lines) if notice in l]
        where = [("상단" if j < len(po.lines) * 0.2 else "하단" if j > len(po.lines) * 0.8 else "중간")
                 for j in pos]
        lines.append(f"  {pkg} p{n}: {len(po.lines)}줄 중 {pos} → {where or '없음'}")
    (args.out_dir / "transcript_skeleton.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # ── 2. vendor overlay separation ─────────────────────────
    over = ["# 벤더 오버레이 분리 — IRS 준거에 없는데 데이터셋에 있는 라벨", "",
            "준거 열이 '없음'이면 IRS 산출물이 아니라 전달 벤더가 찍은 것으로 본다.", ""]
    over += probe_table("오버레이 후보", OVERLAY_CANDIDATES,
                        {**refs, **{f"blank:{k}": v for k, v in blanks.items()}}, studied_objs)
    tokens: dict[str, list[str]] = defaultdict(list)
    for (pkg, n), po in sorted(studied_objs.items()):
        for tok in re.findall(r"\b[a-z0-9]{10}\b", po.fulltext):
            if any(c.isdigit() for c in tok) and any(c.isalpha() for c in tok):
                tokens[tok].append(f"{pkg}:p{n}")
    over += ["## 10자 영숫자 혼합 토큰 (그룹핑 재료 — 값은 마스킹)", ""]
    for tok, pgs in sorted(tokens.items(), key=lambda kv: -len(kv[1])):
        over.append(f"  {mask(tok)!r} → {len(pgs)}p {sorted(set(pgs))}")
    (args.out_dir / "vendor_overlay.txt").write_text("\n".join(over) + "\n", encoding="utf-8")

    # ── 3. per-page classification ───────────────────────────
    irs_full = " ".join(v.fulltext for v in list(refs.values())[:2]) + " " + \
               " ".join(v.fulltext for v in blanks.values())
    value_re = re.compile(r"^[\d\s$,.:%()/x#*-]*$", re.I)
    for pkg, n, raw in studied:
        po = studied_objs[(pkg, n)]
        rows, counts = [], defaultdict(int)
        for ln in po.lines:
            if any(normalize(p) == ln or normalize(p) in ln for p in OVERLAY_CANDIDATES) \
                    and not (len(ln) >= 15 and ln in irs_full):
                cls = "VENDOR_OVERLAY"
            elif len(ln) >= 8 and ln in irs_full:
                cls = "IRS_STANDARD"
            elif value_re.fullmatch(ln):
                cls = "FILLED"
            else:
                cls = "UNCERTAIN"
            counts[cls] += 1
            rows.append(f"[{cls:14}] {mask(ln)}")
        (args.out_dir / f"page_{pkg}_{n:03d}.txt").write_text(
            f"# {pkg} p{n} {dict(counts)}\n" + "\n".join(rows) + "\n", encoding="utf-8")

    # ── 4. p38-style minimal page + 5. pairing materials ─────
    pair = ["# 두 벌 짝 맞추기 재료 (사실만 — 값은 마스킹)", ""]
    for (pkg, n), po in sorted(transcript_objs.items()):
        marker = re.search(r"page (\d+) of (\d+)", po.fulltext)
        period = re.findall(r"tax period requested: *(\S+)|(\d{2}-\d{2}-\d{4})", po.fulltext)
        eins = re.findall(r"x{2}-x{3}\d{4}", po.fulltext)
        toks = sorted({t for t in re.findall(r"\b[a-z0-9]{10}\b", po.fulltext)
                       if any(c.isdigit() for c in t) and any(c.isalpha() for c in t)})
        pair.append(
            f"  {pkg} p{n:>2}: 줄수={len(po.lines):>3} 마커={marker.group(0) if marker else '없음'} "
            f"EIN마스크={[mask(e) for e in sorted(set(eins))]} 토큰={[mask(t) for t in toks]}"
        )
        dates = sorted(set(re.findall(r"\d{2}-\d{2}-\d{4}", po.fulltext)))
        pair.append(f"           날짜값 {len(dates)}종 {[mask(d) for d in dates]}")

    # Values stay unprinted; only whether two pages agree is reported.
    def fields(po: PageText) -> dict:
        return {
            "tax_period": sorted(set(re.findall(r"\b\d{2}-\d{2}-(\d{4})\b", po.fulltext))),
            "ein": sorted(set(re.findall(r"\bx{2}-x{3}(\d{4})\b", po.fulltext))),
            "employer_line": sorted(l for l in po.lines
                                    if l.isupper() or re.fullmatch(r"[a-z ]{8,24}", l)),
            "money": sorted(set(re.findall(r"\$[\d,]+\.\d\d", po.fulltext))),
        }

    pair += ["", "## 페이지 쌍별 일치 여부 (값은 출력하지 않고 같은지만 본다)", ""]
    keys = sorted(transcript_objs)
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            fa, fb = fields(transcript_objs[a]), fields(transcript_objs[b])
            same = {k: (fa[k] == fb[k]) if (fa[k] or fb[k]) else "양쪽 없음" for k in fa}
            overlap = {k: len(set(fa[k]) & set(fb[k])) for k in ("ein", "money", "tax_period")}
            pair.append(f"  {a[1]:>2} ↔ {b[1]:>2}: 일치={same} 교집합크기={overlap}")

    pair += ["", "## 최소 신호 페이지 전수 (껍데기 페이지에 남은 것)", ""]
    for (pkg, n), po in sorted(transcript_objs.items()):
        if len(po.lines) > 10:
            continue
        pair.append(f"  {pkg} p{n} — {len(po.lines)}줄, 원문 {len(po.raw)}자")
        for l in po.lines:
            pair.append(f"      {mask(l)}")
    (args.out_dir / "pairing.txt").write_text("\n".join(pair) + "\n", encoding="utf-8")

    # ── 6. TWN / corelogic ───────────────────────────────────
    twn_page = {k: v for k, v in studied_objs.items() if PKG02_INCOME_PAGES.get(k[1]) == "twn"}
    twn = ["# TWN 샘플 ↔ 데이터셋 라벨 대조", ""]
    twn += probe_table("TWN 라벨", TWN_LABELS, {"TWN_sample": refs["TWN_sample"]}, twn_page)
    (args.out_dir / "twn.txt").write_text("\n".join(twn) + "\n", encoding="utf-8")

    core_page = {k: v for k, v in studied_objs.items() if PKG02_INCOME_PAGES.get(k[1]) == "corelogic"}
    core = ["# Corelogic 검증 페이지 — 준거 없음, 관찰만", ""]
    for (pkg, n), po in core_page.items():
        core.append(f"## {pkg} p{n} ({len(po.lines)}줄)")
        core += [f"  {mask(l)}" for l in po.lines]
    (args.out_dir / "corelogic.txt").write_text("\n".join(core) + "\n", encoding="utf-8")

    # ── 7. P&L vocabulary probe ──────────────────────────────
    pl_page = {k: v for k, v in studied_objs.items() if k[0] == "pkg01_income"}
    pl = ["# P&L 어휘 프로브 — '전형 P&L이라면 있었을 어휘'가 이 표본에 몇 개 있는가", "",
          "프로브 근거: Fannie B3-3.7-04(‘Schedule C와 유사한 형식’) + Schedule C 항목명", ""]
    pl += probe_table("P&L 어휘", PL_VOCAB, {"Fannie_P&L": refs["Fannie_P&L"]}, pl_page)
    for (pkg, n), po in pl_page.items():
        pl += [f"## {pkg} p{n} 전수 ({len(po.lines)}줄, 원문 문자 {len(po.raw)})", ""]
        pl += [f"  {mask(l)}" for l in po.lines]
    (args.out_dir / "pl_probe.txt").write_text("\n".join(pl) + "\n", encoding="utf-8")

    # ── 8. cross contamination ───────────────────────────────
    types = type_map()
    all_objs = {k: PageText.from_raw(v) for k, v in every.items()}
    cc = ["# 교차 오염 — INCOME 후보 어휘가 다른 유형 페이지에 걸리는 정도", "",
          "pkg01 유형은 생성된 GT, pkg02는 config/expected_pages.yaml + 이 스크립트의 income 목록.",
          "어느 쪽에도 없는 페이지는 UNKNOWN으로 집계한다 (조용한 음성 처리 방지).", ""]
    for phrase in CONTAMINATION_PROBES:
        per_type: dict[str, list[str]] = defaultdict(list)
        for (pkg, n), po in all_objs.items():
            if match_phrase(phrase, po):
                per_type[types.get((pkg, n), "UNKNOWN")].append(f"{pkg}:p{n}")
        summary = ", ".join(f"{t}={len(v)}p" for t, v in sorted(per_type.items()))
        cc.append(f"  {phrase!r:22} {summary or '0건'}")
        for t, v in sorted(per_type.items()):
            if t not in ("INCOME_DOC",):
                cc.append(f"        └ {t}: {sorted(v)[:12]}")
    (args.out_dir / "cross_contamination.txt").write_text("\n".join(cc) + "\n", encoding="utf-8")

    # ── 9. unobserved-subgroup vocabulary from IRS blanks ────
    uv = ["# 미관찰 하위군 대비 — IRS blank에서 수집한 대표 식별 문구", "",
          "데이터셋 대조 대상이 아니다. 다음 패키지에 W-2·1040 원본이 들어올 때의 참고 자료.", ""]
    omb_re = re.compile(r"omb no\. \d{4}-\d{4}")
    cat_re = re.compile(r"cat(?:alog)?\.? *(?:no\.?|number) *\d{4,6}[a-z]?")
    for name, po in blanks.items():
        titles = [l for l in po.lines[:40] if 20 <= len(l) <= 90 and not l[0].isdigit()]
        uv.append(f"## Form {name}")
        uv.append(f"  OMB: {sorted(set(omb_re.findall(po.fulltext)))}")
        uv.append(f"  Catalog: {sorted(set(cat_re.findall(po.fulltext)))[:3]}")
        uv.append(f"  상단 후보 문구: {titles[:6]}")
        uv.append("")
    (args.out_dir / "unobserved_vocab.txt").write_text("\n".join(uv) + "\n", encoding="utf-8")

    print(f"준거: NASFAA {len(nasfaa)}p, IRS blank {len(blanks)}종, TWN 샘플, Fannie P&L")
    print(f"데이터셋 대상: {len(studied)}p (pkg02 {len(PKG02_INCOME_PAGES)} + pkg01 P&L)")
    print(f"교차 오염 측정 모집단: {len(all_objs)}p")
    print(f"-> {args.out_dir}")


if __name__ == "__main__":
    main()
