"""Parse every PDF in a data directory and export page-level artifacts.

Usage:
    uv run python -m docsplit.ingest.parse --data-dir data --out-dir outputs

Outputs (under --out-dir):
    parsed/<slug>.jsonl          one JSON record per page (includes raw text)
    inspection/<slug>/page_NNN.txt   raw page text for human review (NNN = 0-based index)
    stats.md / stats.json        aggregate numbers only, no raw text
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .pdf_parser import PageRecord, parse_pdf, slugify
from .stats import compute_file_stats, render_stats_md


def export_jsonl(records: list[PageRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r.to_dict(), ensure_ascii=False) + "\n")


def export_inspection(records: list[PageRecord], dir_path: Path) -> None:
    dir_path.mkdir(parents=True, exist_ok=True)
    for r in records:
        (dir_path / f"page_{r.page_index:03d}.txt").write_text(
            r.raw_text, encoding="utf-8"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--out-dir", type=Path, default=Path("outputs"))
    args = parser.parse_args()

    # recurse into subdirs (packages/, ground_truth/) but skip reference/ —
    # public blank forms are comparison material, not task data
    pdf_paths = sorted(
        p for p in args.data_dir.rglob("*.pdf") if "reference" not in p.parts
    )
    if not pdf_paths:
        raise SystemExit(f"no PDFs found in {args.data_dir}")

    all_stats = []
    for pdf_path in pdf_paths:
        records = parse_pdf(pdf_path)
        slug = slugify(pdf_path.name)
        export_jsonl(records, args.out_dir / "parsed" / f"{slug}.jsonl")
        export_inspection(records, args.out_dir / "inspection" / slug)
        file_stats = compute_file_stats(records)
        all_stats.append(file_stats)
        print(f"{pdf_path.name}: {file_stats.page_count} pages, "
              f"{len(file_stats.empty_pages)} empty")

    (args.out_dir / "stats.json").write_text(
        json.dumps([s.to_dict() for s in all_stats], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (args.out_dir / "stats.md").write_text(render_stats_md(all_stats), encoding="utf-8")
    print(f"wrote {args.out_dir}/stats.md and stats.json")


if __name__ == "__main__":
    main()
