"""One-off observation dump over parsed JSONL files.

For each page: head/tail lines (truncated), plus regex hits for
page-numbering, ID-like fields, and date-like fields. Also reports lines
repeated across >=50% of pages per file (header/footer candidates).

Usage: uv run python scripts/observe_dump.py <jsonl> [<jsonl> ...] > dump.txt
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

HEAD_N = 8
TAIL_N = 4
LINE_TRUNC = 110

PATTERNS = {
    "page_of": re.compile(r"page\s*[:#]?\s*\d+\s*(?:of|/)\s*\d+", re.I),
    "id_field": re.compile(
        r"(?:file\s*(?:no|number|#)|order\s*(?:no|number|#)|loan\s*(?:no|number|#)|"
        r"report\s*(?:id|no|number|#)|case\s*(?:no|number|#)|reference\s*(?:no|number|#)|"
        r"application\s*(?:no|number|#)|account\s*(?:no|number|#)|policy\s*(?:no|number)|"
        r"escrow\s*(?:no|number)|title\s*(?:no|number))\b[^\n]{0,60}",
        re.I,
    ),
    "date_field": re.compile(
        r"(?:report\s*date|effective\s*date|date\s*(?:issued|completed|of\s*report)|"
        r"prepared\s*(?:on|date)|as\s*of)\b[^\n]{0,50}",
        re.I,
    ),
}


def nonempty_lines(text: str) -> list[str]:
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def dump_file(path: Path) -> None:
    records = [json.loads(ln) for ln in path.open(encoding="utf-8")]
    print(f"\n{'=' * 90}\nFILE: {records[0]['source_file']}  ({len(records)} pages)\n{'=' * 90}")

    line_pages: dict[str, list[int]] = {}
    for r in records:
        for ln in set(nonempty_lines(r["raw_text"])):
            line_pages.setdefault(ln, []).append(r["page_index"])

    repeated = {
        ln: pages for ln, pages in line_pages.items() if len(pages) >= max(2, len(records) // 2)
    }
    print("\n-- repeated lines (>=50% of pages) --")
    for ln, pages in sorted(repeated.items(), key=lambda kv: -len(kv[1])):
        print(f"  [{len(pages)}/{len(records)} pages {sorted(pages)}] {ln[:LINE_TRUNC]}")

    for r in records:
        lines = nonempty_lines(r["raw_text"])
        print(f"\n--- page {r['page_index']} ({r['stripped_length']} chars, {r['image_count']} img) ---")
        for ln in lines[:HEAD_N]:
            print(f"  H| {ln[:LINE_TRUNC]}")
        if len(lines) > HEAD_N + TAIL_N:
            print(f"  ...({len(lines) - HEAD_N - TAIL_N} lines omitted)...")
        for ln in lines[-TAIL_N:] if len(lines) > HEAD_N else []:
            print(f"  T| {ln[:LINE_TRUNC]}")
        for name, pat in PATTERNS.items():
            for m in pat.finditer(r["raw_text"]):
                print(f"  {name}> {m.group(0)[:LINE_TRUNC]}")


def main() -> None:
    for arg in sys.argv[1:]:
        dump_file(Path(arg))


if __name__ == "__main__":
    main()
