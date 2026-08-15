"""One-off: match shuffled package pages to original-document pages.

Deterministic text matching: exact raw_text hash first, then a
whitespace-normalized hash as fallback. Prints a mapping table and any
unmatched/ambiguous pages.

Usage:
  uv run python scripts/observe_match.py <shuffled.jsonl> <original.jsonl> [...]
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path


def load(path: Path) -> list[dict]:
    return [json.loads(ln) for ln in path.open(encoding="utf-8")]


def h_exact(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def h_norm(text: str) -> str:
    return hashlib.sha256(re.sub(r"\s+", " ", text).strip().encode()).hexdigest()


def main() -> None:
    shuffled = load(Path(sys.argv[1]))
    exact_idx: dict[str, list[tuple[str, int]]] = {}
    norm_idx: dict[str, list[tuple[str, int]]] = {}
    for arg in sys.argv[2:]:
        for r in load(Path(arg)):
            key = (r["source_file"], r["page_index"])
            exact_idx.setdefault(h_exact(r["raw_text"]), []).append(key)
            norm_idx.setdefault(h_norm(r["raw_text"]), []).append(key)

    unmatched = []
    for r in shuffled:
        exact = exact_idx.get(h_exact(r["raw_text"]), [])
        norm = norm_idx.get(h_norm(r["raw_text"]), [])
        if exact:
            kind = "exact" if len(exact) == 1 else f"exact-ambiguous({len(exact)})"
            print(f"p{r['page_index']:>2} -> {exact} [{kind}]")
        elif norm:
            kind = "normalized" if len(norm) == 1 else f"normalized-ambiguous({len(norm)})"
            print(f"p{r['page_index']:>2} -> {norm} [{kind}]")
        else:
            unmatched.append(r["page_index"])
            print(f"p{r['page_index']:>2} -> UNMATCHED")
    print(f"\nunmatched: {unmatched or 'none'}")


if __name__ == "__main__":
    main()
