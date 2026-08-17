"""Ground-truth builder for packages that ship an answer key.

The ONLY module allowed to look at the original (unshuffled) documents.
Classification/grouping code takes shuffled input exclusively — enforced by
this module being imported only from the evaluation path.

Matching: SHA-256 over raw page text (exact for every page of the sample
package; see the observation notes).

A package whose pages do not all match is not an error — the second package
simply has no answer key. Coverage is returned so the caller can decide.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def build_ground_truth(
    answer_keys: dict[str, str],
    parsed_dir: Path,
    package_jsonl: Path,
    out_path: Path | None = None,
) -> tuple[list[dict], float]:
    """Match a package's pages to the answer-key originals.

    ``answer_keys`` maps original file name -> document type (from discovery).
    Returns (rows, coverage) where coverage is the matched fraction; rows are
    only written out when coverage is complete.
    """
    shuffled = [json.loads(l) for l in package_jsonl.open(encoding="utf-8")]
    if not answer_keys or not shuffled:
        return [], 0.0

    index: dict[str, tuple[str, int]] = {}
    for f in sorted(parsed_dir.glob("*.jsonl")):
        for rec in (json.loads(l) for l in f.open(encoding="utf-8")):
            if rec["source_file"] in answer_keys:
                index[_sha(rec["raw_text"])] = (rec["source_file"], rec["page_index"])

    rows = []
    for rec in shuffled:
        src = index.get(_sha(rec["raw_text"]))
        if src is None:
            continue
        rows.append(
            {
                "input_page": rec["page_index"],
                "document_type": answer_keys[src[0]],
                "source_document": src[0],
                "source_page": src[1],
            }
        )

    coverage = len(rows) / len(shuffled)
    if out_path is not None and coverage == 1.0:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return rows, coverage
