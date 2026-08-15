"""One-off: compare dataset URLA pages against official blank URLA forms.

Classifies each dataset text line as:
  STANDARD   - exact normalized match to a blank-form line
  STANDARD~  - punctuation-normalized / wrapped / fuzzy match to blank text
  RENDERER   - known renderer print codes
  FILLED?    - numeric/currency/date-only line (heuristic)
  UNMATCHED  - none of the above (for manual review)

Also does a reverse pass: blank-form lines never seen in the dataset pages.

Usage:
  uv run python scripts/observe_urla_diff.py --out-dir outputs/urla_standard_diff
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import unicodedata
from pathlib import Path

import pymupdf

REPO = Path(__file__).resolve().parent.parent
BLANKS = {
    "borrower_information": "urla_borrower_information_blank.pdf",
    "additional_borrower": "urla_additional_borrower_blank.pdf",
    "unmarried_addendum": "urla_unmarried_addendum_blank.pdf",
    "lender_loan_information": "urla_lender_loan_information_blank.pdf",
    "continuation_sheet": "urla_continuation_sheet_blank.pdf",
    # Fannie Mae copies of the same joint form (text layer differs from Freddie's)
    "fnm_borrower_information": "fanniemae/URLA-2019-Borrower-v28.pdf",
    "fnm_lender_loan_information": "fanniemae/URLA-2019-Lender-v28.pdf",
}
DATASET = [
    ("pkg01_urla", "outputs/parsed/1003_-_URLA_sample01.jsonl", None),
    ("pkg02_shuffled", "outputs/parsed/02.sample02_shuffled.jsonl",
     [12, 15, 17, 19, 22, 24, 28, 34, 36, 42]),
]
RENDERER_CODES = {"gurla20s", "gurla20_s", "(pod)", "0718"}
VALUE_RE = re.compile(r"^[\d\s$,./:%()\-#xX]*$")  # digits/currency/date-ish only


def norm(line: str) -> str:
    s = unicodedata.normalize("NFKC", line)
    s = s.replace("•", "·").replace("—", "-").replace("–", "-")
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


def blank_pages() -> list[tuple[str, int, list[str]]]:
    out = []
    for comp, fname in BLANKS.items():
        with pymupdf.open(REPO / "data/reference/urla" / fname) as doc:
            for page in doc:
                lines = [l for l in (norm(x) for x in page.get_text().splitlines()) if l]
                out.append((comp, page.number, lines))
    return out


def dataset_pages() -> list[tuple[str, int, list[str]]]:
    out = []
    for label, path, keep in DATASET:
        for rec in (json.loads(l) for l in (REPO / path).open()):
            if keep is not None and rec["page_index"] not in keep:
                continue
            raw = [l for l in rec["raw_text"].splitlines() if l.strip()]
            out.append((label, rec["page_index"], raw))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", type=Path, default=REPO / "outputs/urla_standard_diff")
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    blanks = blank_pages()
    std_lines: dict[str, list[tuple[str, int]]] = {}
    for comp, pno, lines in blanks:
        for ln in lines:
            std_lines.setdefault(ln, []).append((comp, pno))
    std_fulltext = " ".join(ln for _, _, lines in blanks for ln in lines)
    std_keys = list(std_lines)

    seen_std: set[str] = set()
    unmatched_agg: dict[str, list[str]] = {}

    for label, pno, raw_lines in dataset_pages():
        rows = []
        counts = {"STANDARD": 0, "STANDARD~": 0, "RENDERER": 0, "FILLED?": 0, "UNMATCHED": 0}
        for raw in raw_lines:
            n = norm(raw)
            if n in std_lines:
                cls, ref = "STANDARD", std_lines[n][0]
                seen_std.add(n)
            elif n in RENDERER_CODES:
                cls, ref = "RENDERER", None
            elif VALUE_RE.fullmatch(n):
                cls, ref = "FILLED?", None
            elif len(n) >= 15 and n in std_fulltext:
                cls, ref = "STANDARD~", ("wrapped",)
                seen_std.add(n)
            else:
                near = difflib.get_close_matches(n, std_keys, n=1, cutoff=0.90)
                if near and len(n) >= 12:
                    cls, ref = "STANDARD~", ("fuzzy", near[0][:60])
                    seen_std.add(near[0])
                else:
                    cls, ref = "UNMATCHED", None
                    unmatched_agg.setdefault(n, []).append(f"{label}:p{pno}")
            counts[cls] += 1
            rows.append(f"[{cls:9}] {raw.strip()[:100]}" + (f"  <- {ref}" if ref else ""))
        out = args.out_dir / f"{label}_p{pno:03d}.txt"
        out.write_text(
            f"# {label} page {pno}  {counts}\n" + "\n".join(rows) + "\n", encoding="utf-8"
        )
        print(f"{label} p{pno:>2}: {counts}")

    agg = args.out_dir / "unmatched_distinct.txt"
    with agg.open("w", encoding="utf-8") as f:
        for ln, pages in sorted(unmatched_agg.items(), key=lambda kv: -len(kv[1])):
            f.write(f"[{len(pages):2}x {','.join(sorted(set(pages))[:6])}] {ln[:120]}\n")
    print(f"\ndistinct UNMATCHED lines: {len(unmatched_agg)} -> {agg}")

    rev = args.out_dir / "standard_lines_not_seen.txt"
    ds_fulltext = " ".join(
        norm(l) for _, _, lines in dataset_pages() for l in lines
    )
    missing = []
    for ln, refs in std_lines.items():
        if ln in seen_std or ln in ds_fulltext:
            continue
        missing.append((refs[0], ln))
    with rev.open("w", encoding="utf-8") as f:
        for ref, ln in sorted(missing):
            f.write(f"[{ref[0]} p{ref[1]}] {ln[:120]}\n")
    print(f"standard lines never seen in dataset: {len(missing)} -> {rev}")


if __name__ == "__main__":
    main()
