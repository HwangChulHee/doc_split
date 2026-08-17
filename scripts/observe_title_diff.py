"""One-off: compare dataset title pages against association forms and vendor guides.

TITLE differs from the two earlier comparisons in that no single reference covers
the dataset — the two packages use different forms issued by different vendors:

  pkg01  CLTA Preliminary Report   (Fidelity National, CA)
  pkg02  2021 ALTA Commitment      (First American, VA)

so each side gets its own reference and its own evidence grade:

  ALTA blank (association form, via a state regulator's public library)
      -> normative for pkg02
  CLTA guide (title-company publication reproducing an annotated CLTA sample)
      -> vendor-document grade for pkg01; the association form itself is paywalled
  CA Insurance Code 12340.11 (statute)
      -> normative context for the pkg01 front-page disclaimers

This script only reports; it decides nothing.

Outputs (outputs/title_standard_diff/):
  alta_notice.txt      the "This page is only a part of..." notice, per page vs the form
  structure_terms.txt  Schedule/Commitment structure names in form vs dataset
  repeated_lines.txt   lines repeated across pages, per package
  page_<pkg>_<n>.txt   per-page line classification
  set_diff.txt         pkg02 two-instance pairwise differences (values masked)
  shared_vocab.txt     title vocabulary shared by both packages
  cross_check.txt      association phrases of one form appearing in the other package

Usage:
  uv run python scripts/observe_title_diff.py --out-dir outputs/title_standard_diff
"""

from __future__ import annotations

import argparse
import difflib
import html
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import pymupdf

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
from docsplit.rules.normalize import PageText, match_phrase, normalize  # noqa: E402

REF = REPO / "data/reference/title"
ALTA_FORM = REF / "alta/alta_commitment_2021_floir.pdf"
CLTA_GUIDE = REF / "vendors/ticor_how_to_read_prelim_2023.html"
CA_STATUTE = REF / "clta/ca_ins_code_12340_11.html"

# File names carry loan numbers, so they are discovered rather than hardcoded
# (same convention as scripts/observe_credit_diff.py).
PKG01_TITLE_GLOB = "Title_Report*.jsonl"
PACKAGE_GLOB = "*_shuffled.jsonl"
PKG02_TITLE_TEXT_PAGES = [0, 2, 4, 6, 8, 14, 16, 21, 32, 41]
PKG02_TITLE_SCAN_PAGES = [10, 25, 39]  # image-only; counted, never read here

# The ALTA notice carries optional segments in square brackets. An issued
# commitment drops the brackets and either keeps or omits the content, so the
# form line has to be expanded into variants before comparing.
BRACKET_RE = re.compile(r"\[([^\]]*)\]")

VALUE_RE = re.compile(r"^[\d\s$,.:%()/#-]*$")
DATE_RE = re.compile(r"^\d{1,2}/\d{1,2}/\d{2,4}$|^[a-z]+ \d{1,2}, \d{4}$")
# Bare list markers ("1.", "a.", "iii.") carry no evidence either way
ENUM_RE = re.compile(r"[ivx0-9a-z]{1,4}[.)]")

# Fixed vendor/renderer elements observed in the dataset. Checked before the
# association forms so that a state-modified or renderer-added line is not
# credited to the association.
VENDOR_PATTERNS = {
    # pkg01 — Fidelity National / CLTA prelim renderer
    r"^clta preliminary report form \(\d\d/\d\d/\d{4}\)$": "pkg01 폼 버전 푸터",
    r"^printed: ": "pkg01 인쇄 타임스탬프",
    r"^page \d+$": "pkg01 페이지 표기 (분모 없음)",
    r"^ca-[a-z]{2}-[a-z]+-$": "pkg01 푸터 코드 앞부분",
    r"^-sps-\d+-\d+-$": "pkg01 푸터 코드 뒷부분",
    r"fidelity national title": "pkg01 벤더명",
    r"^prelim number:$|^prelim no\.": "pkg01 문서번호 라벨",
    r"^amendment \d+$": "pkg01 개정 회차",
    r"^title officer:$|^file no\.:$|^ref\. no\.:$": "pkg01 헤더 라벨",
    # pkg02 — First American / ALTA commitment renderer
    r"^form \d{6,9} \(\d+-\d+-\d+\)$": "pkg02 벤더 폼 코드",
    r"^page \d+ of \d+$|^page \d+ of$": "pkg02 페이지 마커",
    r"^[a-z ]+ - 2021 v\.$": "pkg02 주별 버전 표기 (앞부분)",
    r"first american title insurance company": "pkg02 벤더명",
    # The issuing agent's own name is deployment-level (one office, one deal), so
    # it is deliberately not encoded here — those lines fall through to UNCERTAIN.
}

# Structure names to compare between form and dataset, with punctuation variants
STRUCTURE_TERMS = [
    "Commitment to Issue Policy",
    "Commitment Conditions",
    "Schedule A",
    "Schedule B, Part I—Requirements",
    "Schedule B, Part I - Requirements",
    "SCHEDULE B, PART I—Requirements",
    "Schedule B, Part II—Exceptions",
    "Schedule B, Part II - Exceptions",
    "SCHEDULE B, PART II—Exceptions",
    "Requirements",
    "Exceptions",
    "NOTICE",
    "PRELIMINARY REPORT",
    "EXHIBIT A",
    "Legal Description",
    "EXCEPTIONS",
    "REQUIREMENTS",
    "INFORMATIONAL NOTES",
    "END OF EXCEPTIONS",
    "END OF REQUIREMENTS",
]

# Verbatim label/sentence blocks of the ALTA blank — checked one by one so the
# report can say which of the form's fixed text survives into an issued document.
ALTA_FORM_LABELS = [
    "Transaction Identification Data, for which the Company assumes no liability",
    "Commitment Condition 5.e.", "Issuing Agent:", "Issuing Office:",
    "Issuing Office’s ALTA® Registry ID:", "Loan ID Number:", "Commitment Number:",
    "Issuing Office File Number:", "Property Address:", "Revision Number:",
    "Commitment Date:", "Policy to be issued:", "Proposed Insured:",
    "Proposed Amount of Insurance:", "The estate or interest to be insured:",
    "The estate or interest in the Land at the Commitment Date is",
    "The Title is, at the Commitment Date, vested in:",
    "as disclosed in the Public Records, has been since",
    "The Land is described as follows:",
    "All of the following Requirements must be met:",
    "The Proposed Insured must notify the Company in writing of the name of any party",
    "Pay the agreed amount for the estate or interest to be insured.",
    "Pay the premiums, fees, and charges for the Policy to the Company.",
    "Documents satisfactory to the Company that convey the Title or create the Mortgage",
    "Some historical land records contain Discriminatory Covenants that are illegal",
    "Only the remaining provisions of the document will be excepted from coverage.",
    "The Policy will not insure against loss or damage resulting from the terms and conditions",
    "Any defect, lien, encumbrance, adverse claim, or other matter that appears for the first time",
    "2021 ALTA® Owner’s Policy", "2021 ALTA® Loan Policy", "ALTA® Homeowner’s Policy",
    "BLANK TITLE INSURANCE COMPANY", "Authorized Signatory",
    # renderer typo candidate — the dataset prints a lowercase L for the capital I
    "lssuing Office:",
]

# Domain vocabulary candidates — checked in both packages (design-neutral survey)
SHARED_VOCAB = [
    "Title Insurance", "title insurance", "Legal Description", "easement",
    "lien", "vested in", "Deed of Trust", "deed of trust", "Trustee",
    "Beneficiary", "Recording Date", "Official Records", "APN", "Parcel",
    "Property taxes", "policy of title insurance", "Schedule A", "Exceptions",
    "Requirements", "Company", "Land", "estate or interest", "encumbrance",
    "covenants, conditions", "Amount of Insurance", "Proposed Insured",
    "recorded", "County", "assessments", "arbitration",
]

# Front-page sentences of the CLTA prelim that the vendor guide annotates as
# California-law-required (see docs/analysis/title_standard_analysis.md §4).
CLTA_REQUIRED_SENTENCES = [
    "It is important to note that this preliminary report is not a written representation "
    "as to the condition of title and may not list all liens, defects, and encumbrances "
    "affecting title to the land.",
    "The exceptions and exclusions are meant to provide you with notice of matters which "
    "are not covered under the terms of the title insurance policy and should be carefully "
    "considered.",
    "This report (and any supplements or amendments hereto) is issued solely for the purpose "
    "of facilitating the issuance of a policy of title insurance and no liability is assumed hereby.",
]


# ── reference loading ────────────────────────────────────────
def html_text(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    raw = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
    return html.unescape(re.sub(r"(?is)<[^>]+>", "\n", raw))


def alta_form() -> tuple[PageText, list[str]]:
    with pymupdf.open(ALTA_FORM) as doc:
        pages = [pg.get_text() for pg in doc]
    return PageText.from_raw("\n".join(pages)), pages


def squash(text: str) -> str:
    """Absorb whitespace around dashes — the blank wraps 'Part II—\\nExceptions'."""
    return re.sub(r"\s*-\s*", "-", text)


def blank_match(form_variant: str, got: str) -> bool:
    """Same as squash-compare, but the form's fill-in blank matches any issuer."""
    pattern = re.sub(r"_{2,}", ".+?", re.escape(squash(form_variant).rstrip(".")))
    return re.fullmatch(pattern, squash(got).rstrip(".")) is not None


def notice_variants(form_line: str) -> dict[str, str]:
    """Expand the bracketed optional segments of the ALTA notice."""
    segments = BRACKET_RE.findall(form_line)
    out = {}
    for mask in range(1 << len(segments)):
        i = -1

        def repl(_m: re.Match) -> str:
            nonlocal i
            i += 1
            return _m.group(1) if mask >> i & 1 else ""

        label = "".join("K" if mask >> b & 1 else "-" for b in range(len(segments)))
        out[label] = normalize(BRACKET_RE.sub(repl, form_line))
    return out


# ── dataset loading ──────────────────────────────────────────
def dataset_pages() -> list[tuple[str, int, str]]:
    parsed = REPO / "outputs/parsed"
    title01 = next(iter(sorted(parsed.glob(PKG01_TITLE_GLOB))), None)
    packages = sorted(parsed.glob(PACKAGE_GLOB))
    if title01 is None or len(packages) < 2:
        raise SystemExit(
            f"{parsed} 에서 대상 파일을 찾지 못했습니다 — 먼저 파싱을 실행하세요: "
            "uv run python -m docsplit.ingest.parse"
        )
    out = []
    for rec in (json.loads(l) for l in title01.open(encoding="utf-8")):
        out.append(("pkg01", rec["page_index"], rec["raw_text"]))
    wanted = set(PKG02_TITLE_TEXT_PAGES)
    for rec in (json.loads(l) for l in packages[1].open(encoding="utf-8")):
        if rec["page_index"] in wanted:
            out.append(("pkg02", rec["page_index"], rec["raw_text"]))
    return out


def mask_values(line: str) -> str:
    """Keep the shape of a line while dropping the values it carries."""
    s = re.sub(r"\d", "#", line)
    return s[:110]


def classify_line(
    line: str, alta_lines: set[str], alta_full: str, clta_full: str, notices: str = ""
) -> str:
    if ENUM_RE.fullmatch(line):
        return "ENUM"
    # The notice wraps mid-sentence and its filled-in slot carries the issuer's
    # name, so a fragment of it would otherwise be charged to the vendor.
    if len(line) >= 15 and squash(line) in notices:
        return "ASSOC_STANDARD(notice)"
    for pattern in VENDOR_PATTERNS:
        if re.search(pattern, line):
            return "VENDOR"
    if len(line) >= 4 and line in alta_lines:
        return "ASSOC_STANDARD"
    if len(line) >= 15 and line in alta_full:
        return "ASSOC_STANDARD~"
    if len(line) >= 15 and line in clta_full:
        return "ASSOC_STANDARD(clta-ref)"
    if VALUE_RE.fullmatch(line) or DATE_RE.fullmatch(line):
        return "FILLED"
    return "UNCERTAIN"


def filled_notices(variant: str, page_objs: dict) -> str:
    """The form's notice with its issuer blank filled by what the pages show.

    Not circular: the sentence frame comes from the association form; only the
    fill-in slot is taken from the data.
    """
    issuers = set()
    for po in page_objs.values():
        m = re.search(r"commitment for title insurance issued by (.+?)\. this commitment", po.fulltext)
        if m:
            issuers.add(m.group(1))
    return " ".join(squash(variant.replace("________", i)) for i in sorted(issuers))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=Path, default=REPO / "outputs/title_standard_diff")
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    alta, alta_raw_pages = alta_form()
    alta_lines = set(alta.lines)
    clta_ref = PageText.from_raw(html_text(CLTA_GUIDE) + "\n" + html_text(CA_STATUTE))

    pages = dataset_pages()
    page_objs = {(pkg, n): PageText.from_raw(txt) for pkg, n, txt in pages}
    pkg_pages = defaultdict(list)
    for pkg, n, _ in pages:
        pkg_pages[pkg].append(n)

    # ── 1. the ALTA notice ───────────────────────────────────
    form_notice = next(
        l for l in alta_raw_pages[0].splitlines() if "only a part of" in l
    ).strip()
    # the notice wraps across source lines; rebuild it from the form's fulltext
    m = re.search(
        r"this page is only a part of.*?electronic form\]?\.?", alta.fulltext
    )
    form_notice_full = m.group(0) if m else normalize(form_notice)
    variants = notice_variants(form_notice_full)
    notices = filled_notices(variants["K-K"], page_objs)

    lines = ["# ALTA 고지문 대조 — 'This page is only a part of ...'", "",
             "## 폼(협회 blank) 원문 — 대괄호는 선택 구간", "", form_notice_full, "",
             "## 대괄호 조합별 변형 (K=유지, -=생략)", ""]
    for label, text in sorted(variants.items()):
        lines.append(f"[{label}] {text}")
    lines += ["", "## 데이터셋 페이지별 확인", "",
              "판정 단계: ① 원문 그대로 ② 대시 주변 공백 흡수(폼의 줄바꿈 흔적 제거)",
              "           ③ 발행사 공란(________)을 임의 문자열로 허용", ""]
    for (pkg, n), po in sorted(page_objs.items()):
        found = re.search(r"this page is only a part of.*?electronic form\.", po.fulltext)
        if not found:
            lines.append(f"{pkg} p{n:>2}: 없음")
            continue
        got = found.group(0)
        exact = [lb for lb, v in variants.items() if v.rstrip(".") == got.rstrip(".")]
        squashed = [lb for lb, v in variants.items() if squash(v) == squash(got)]
        filled = [lb for lb, v in variants.items() if blank_match(v, got)]
        lines.append(
            f"{pkg} p{n:>2}: 있음 ({len(got)}자) ①={exact or '-'} ②={squashed or '-'} ③={filled or '-'}"
        )
        if not filled:
            lines.append(f"          got: {got}")
    lines += ["", "## Copyright 블록", ""]
    for phrase in ("Copyright 2021 American Land Title Association. All rights reserved.",
                   "The use of this Form (or any derivative thereof) is restricted to ALTA licensees",
                   "Reprinted under license from the American Land Title Association."):
        in_form = match_phrase(phrase, alta) is not None
        hits = sorted(f"{p}:p{n}" for (p, n), po in page_objs.items() if match_phrase(phrase, po))
        lines.append(f"  {phrase[:60]!r:64} form={in_form} dataset={len(hits)}p {hits}")
    (args.out_dir / "alta_notice.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # ── 2. structure terms ───────────────────────────────────
    rows = ["# 구조 명칭 표기 대조 (폼 vs 데이터셋)", ""]
    for term in STRUCTURE_TERMS:
        in_form = match_phrase(term, alta) is not None
        p1 = sorted(n for (pkg, n), po in page_objs.items() if pkg == "pkg01" and match_phrase(term, po))
        p2 = sorted(n for (pkg, n), po in page_objs.items() if pkg == "pkg02" and match_phrase(term, po))
        rows.append(f"  {term!r:42} alta_form={str(in_form):5} pkg01={p1} pkg02={p2}")
    rows += ["", "# ALTA blank 고정 라벨·문장이 발행본에 남아 있는가", ""]
    for term in ALTA_FORM_LABELS:
        in_form = match_phrase(term, alta) is not None
        # fuzzy hits are reported separately: at 0.90 they conflate near-identical
        # labels (e.g. a capital-I / lowercase-l typo), which is itself a finding
        hits = {n: m.method for (pkg, n), po in page_objs.items()
                if pkg == "pkg02" and (m := match_phrase(term, po))}
        exact = sorted(n for n, meth in hits.items() if meth != "fuzzy")
        fuzzy = sorted(n for n, meth in hits.items() if meth == "fuzzy")
        rows.append(f"  {term[:58]!r:62} alta_form={str(in_form):5} "
                    f"pkg02_exact={exact} pkg02_fuzzy={fuzzy}")
    (args.out_dir / "structure_terms.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")

    # ── 3. repeated lines per package ────────────────────────
    rep_lines = ["# 패키지별 반복 라인 (2페이지 이상)", ""]
    for pkg in ("pkg01", "pkg02"):
        counts: dict[str, list[int]] = defaultdict(list)
        for (p, n), po in page_objs.items():
            if p != pkg:
                continue
            for ln in set(po.lines):
                counts[ln].append(n)
        total = len(pkg_pages[pkg])
        rep_lines.append(f"## {pkg} (총 {total}p)")
        for ln, pgs in sorted(counts.items(), key=lambda kv: (-len(kv[1]), kv[0])):
            if len(pgs) < 2:
                continue
            cls = classify_line(ln, alta_lines, alta.fulltext, clta_ref.fulltext, notices)
            rep_lines.append(f"  [{len(pgs):2}/{total} {cls:24}] {mask_values(ln)}")
        rep_lines.append("")
    (args.out_dir / "repeated_lines.txt").write_text("\n".join(rep_lines) + "\n", encoding="utf-8")

    # ── 4. per-page classification ───────────────────────────
    uncertain: dict[str, list[str]] = defaultdict(list)
    for pkg, n, _ in pages:
        po = page_objs[(pkg, n)]
        rows, counts = [], defaultdict(int)
        for ln in po.lines:
            cls = classify_line(ln, alta_lines, alta.fulltext, clta_ref.fulltext, notices)
            counts[cls] += 1
            if cls == "UNCERTAIN":
                uncertain[ln].append(f"{pkg}:p{n}")
            rows.append(f"[{cls:24}] {ln[:110]}")
        (args.out_dir / f"page_{pkg}_{n:03d}.txt").write_text(
            f"# {pkg} p{n} {dict(counts)}\n" + "\n".join(rows) + "\n", encoding="utf-8"
        )
    with (args.out_dir / "uncertain_lines.txt").open("w", encoding="utf-8") as f:
        for ln, pgs in sorted(uncertain.items(), key=lambda kv: -len(kv[1])):
            f.write(f"[{len(pgs):3}x {','.join(sorted(set(pgs))[:6])}] {mask_values(ln)}\n")

    # ── 5. pkg02 two-instance pairwise diff (values masked) ──
    marker_re = re.compile(r"page (\d+) of (\d+)?")
    by_marker: dict[str, list[int]] = defaultdict(list)
    for (pkg, n), po in page_objs.items():
        if pkg != "pkg02":
            continue
        mm = marker_re.search(po.fulltext)
        by_marker[mm.group(1) if mm else "?"].append(n)

    diff_lines = ["# pkg02 Commitment 두 벌 대조 (값은 마스킹)", "",
                  "쌍은 페이지 마커(Page N of 5)로 묶었다.", ""]
    for slot, pgs in sorted(by_marker.items()):
        diff_lines.append(f"## Page {slot} of 5 -> 데이터셋 페이지 {sorted(pgs)}")
        if len(pgs) != 2:
            diff_lines += [f"  (쌍이 아님: {len(pgs)}장)", ""]
            continue
        a, b = sorted(pgs)
        la, lb = page_objs[("pkg02", a)].lines, page_objs[("pkg02", b)].lines
        diff_lines.append(f"  공통 라인 {len(set(la) & set(lb))} / p{a} {len(la)} / p{b} {len(lb)}")

        # Line-set diff is dominated by re-wrapping, so the field-level answer
        # comes from a word diff of the rejoined text instead.
        wa = page_objs[("pkg02", a)].fulltext.split()
        wb = page_objs[("pkg02", b)].fulltext.split()
        sm = difflib.SequenceMatcher(None, wa, wb, autojunk=False)
        diff_lines.append(f"  단어 일치율 {sm.ratio():.4f} (p{a} {len(wa)}단어 / p{b} {len(wb)}단어)")
        real = 0
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                continue
            left, right = " ".join(wa[i1:i2]), " ".join(wb[j1:j2])
            ctx = " ".join(wa[max(0, i1 - 6):i1])
            real += 1
            diff_lines += [
                f"    [{tag}] ...{ctx[-60:]!r} 뒤",
                f"        p{a}: {mask_values(left)!r}",
                f"        p{b}: {mask_values(right)!r}",
            ]
        if not real:
            diff_lines.append("    (단어 수준 차이 없음 — 두 페이지의 텍스트가 동일)")
        diff_lines.append("")
    (args.out_dir / "set_diff.txt").write_text("\n".join(diff_lines) + "\n", encoding="utf-8")

    # ── 6. cross check + shared vocabulary ───────────────────
    cross = ["# 교차 확인", "", "## ALTA 폼 고정 문구가 pkg01(CLTA)에도 나타나는가", ""]
    alta_probes = [
        "This page is only a part of a 2021 ALTA Commitment",
        "Copyright 2021 American Land Title Association",
        "Commitment Conditions", "Commitment to Issue Policy",
        "Schedule B, Part I—Requirements", "Proposed Insured",
        "Amount of Insurance", "Knowledge", "Public Records",
        "ALTA", "American Land Title Association",
    ]
    for phrase in alta_probes:
        p1 = sorted(n for (pkg, n), po in page_objs.items() if pkg == "pkg01" and match_phrase(phrase, po))
        p2 = sorted(n for (pkg, n), po in page_objs.items() if pkg == "pkg02" and match_phrase(phrase, po))
        cross.append(f"  {phrase!r:52} pkg01={p1} pkg02={len(p2)}p")
    cross += ["", "## CLTA 쪽 법정 성격 문장이 pkg02에도 나타나는가", ""]
    for sent in CLTA_REQUIRED_SENTENCES:
        p1 = sorted(n for (pkg, n), po in page_objs.items() if pkg == "pkg01" and match_phrase(sent, po))
        p2 = sorted(n for (pkg, n), po in page_objs.items() if pkg == "pkg02" and match_phrase(sent, po))
        in_guide = match_phrase(sent, clta_ref) is not None
        cross.append(f"  guide={in_guide} pkg01={p1} pkg02={p2}  {sent[:70]}...")
    (args.out_dir / "cross_check.txt").write_text("\n".join(cross) + "\n", encoding="utf-8")

    vocab = ["# 두 패키지 공유 어휘 후보", "", "term | pkg01 pages | pkg02 pages", ""]
    for term in SHARED_VOCAB:
        p1 = sorted(n for (pkg, n), po in page_objs.items() if pkg == "pkg01" and match_phrase(term, po))
        p2 = sorted(n for (pkg, n), po in page_objs.items() if pkg == "pkg02" and match_phrase(term, po))
        flag = "SHARED" if p1 and p2 else ("pkg01만" if p1 else ("pkg02만" if p2 else "없음"))
        vocab.append(f"  {term!r:30} {flag:7} pkg01={len(p1)}p {p1}  pkg02={len(p2)}p {p2}")
    (args.out_dir / "shared_vocab.txt").write_text("\n".join(vocab) + "\n", encoding="utf-8")

    # ── console summary ──────────────────────────────────────
    print(f"ALTA 폼: {ALTA_FORM.name} {len(alta_raw_pages)}p, 라인 {len(alta_lines)}종")
    print(f"CLTA 참조: {CLTA_GUIDE.name} + {CA_STATUTE.name} ({len(clta_ref.lines)} 라인)")
    print(f"데이터셋: pkg01 {len(pkg_pages['pkg01'])}p, "
          f"pkg02 텍스트 {len(pkg_pages['pkg02'])}p (스캔 {len(PKG02_TITLE_SCAN_PAGES)}p 제외)")
    print(f"UNCERTAIN 고유 라인: {len(uncertain)}")
    print(f"-> {args.out_dir}")


if __name__ == "__main__":
    main()
