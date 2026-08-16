"""Ground-truth builder for a package that ships an answer key.

The ONLY module allowed to look at the original (unshuffled) documents.
Classification/grouping code takes shuffled input exclusively — enforced by
this module being imported only from the evaluation path.

Matching: SHA-256 over raw page text (exact for every page of the sample
package; see the observation notes).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

# Original filename fragment -> document type (pkg01 answer key)
ORIGINAL_TYPE_MAP = {
    "1003 - URLA": "URLA_1003",
    "Credit Report": "CREDIT_REPORT",
    "INCOME": "INCOME_DOC",
    "Title Report": "TITLE_REPORT",
}


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _doc_type(source_file: str) -> str:
    for frag, dtype in ORIGINAL_TYPE_MAP.items():
        if source_file.startswith(frag):
            return dtype
    raise ValueError(f"원본 파일명에서 유형을 결정할 수 없음: {source_file}")


def build_ground_truth(
    data_dir: Path, parsed_dir: Path, package_jsonl: Path, out_path: Path
) -> list[dict]:
    """Match shuffled package pages to original pages and write GT JSONL.

    Originals are whatever sits in ``data/ground_truth/``; the shuffled side is
    the parsed JSONL of the package being verified.
    """
    shuffled = [json.loads(l) for l in package_jsonl.open(encoding="utf-8")]
    originals = {p.name for p in (data_dir / "ground_truth").glob("*.pdf")}
    if not originals:
        raise SystemExit(f"{data_dir / 'ground_truth'} 에 원본 PDF가 없어 GT를 만들 수 없습니다.")

    index: dict[str, tuple[str, int]] = {}
    for f in sorted(parsed_dir.glob("*.jsonl")):
        for rec in (json.loads(l) for l in f.open(encoding="utf-8")):
            if rec["source_file"] in originals:
                index[_sha(rec["raw_text"])] = (rec["source_file"], rec["page_index"])

    rows = []
    for rec in shuffled:
        src = index.get(_sha(rec["raw_text"]))
        if src is None:
            raise RuntimeError(f"GT 매칭 실패: {package_jsonl.stem} p{rec['page_index']}")
        rows.append(
            {
                "input_page": rec["page_index"],
                "document_type": _doc_type(src[0]),
                "source_document": src[0],
                "source_page": src[1],
            }
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return rows
