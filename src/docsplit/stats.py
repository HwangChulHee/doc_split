"""Summary statistics over parsed page records.

Aggregate numbers only — raw page text never appears in the outputs here.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, asdict

from .pdf_parser import PageRecord

SHORT_PAGE_THRESHOLD = 50  # stripped chars
SUSPICIOUS_RATIO_THRESHOLD = 0.05


@dataclass
class FileStats:
    source_file: str
    page_count: int
    text_length_min: int
    text_length_max: int
    text_length_mean: float
    text_length_median: float
    empty_pages: list[int]  # 0-based page indices
    short_pages: list[int]  # 0 < stripped_length < SHORT_PAGE_THRESHOLD
    suspicious_pages: list[int]  # suspicious_char_ratio > threshold
    image_only_pages: list[int]  # is_empty and image_count > 0
    pages_with_images: int

    def to_dict(self) -> dict:
        return asdict(self)


def compute_file_stats(records: list[PageRecord]) -> FileStats:
    lengths = [r.text_length for r in records]
    return FileStats(
        source_file=records[0].source_file,
        page_count=len(records),
        text_length_min=min(lengths),
        text_length_max=max(lengths),
        text_length_mean=round(statistics.mean(lengths), 1),
        text_length_median=statistics.median(lengths),
        empty_pages=[r.page_index for r in records if r.is_empty],
        short_pages=[
            r.page_index for r in records if 0 < r.stripped_length < SHORT_PAGE_THRESHOLD
        ],
        suspicious_pages=[
            r.page_index
            for r in records
            if r.suspicious_char_ratio > SUSPICIOUS_RATIO_THRESHOLD
        ],
        image_only_pages=[
            r.page_index for r in records if r.is_empty and r.image_count > 0
        ],
        pages_with_images=sum(1 for r in records if r.image_count > 0),
    )


def render_stats_md(all_stats: list[FileStats]) -> str:
    lines = [
        "# Parsing stats",
        "",
        "Native PyMuPDF text extraction. Page indices are 0-based.",
        f"Short page: 0 < stripped length < {SHORT_PAGE_THRESHOLD} chars. "
        f"Suspicious: replacement/control/private-use char ratio > {SUSPICIOUS_RATIO_THRESHOLD}.",
        "",
        "| file | pages | len min | len max | len mean | len median | empty | short | suspicious | image-only | pages w/ images |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for s in all_stats:
        lines.append(
            f"| {s.source_file} | {s.page_count} | {s.text_length_min} | {s.text_length_max} "
            f"| {s.text_length_mean} | {s.text_length_median} | {len(s.empty_pages)} "
            f"| {len(s.short_pages)} | {len(s.suspicious_pages)} | {len(s.image_only_pages)} "
            f"| {s.pages_with_images} |"
        )
    lines.append("")
    for s in all_stats:
        lines += [f"## {s.source_file}", ""]
        lines.append(f"- empty pages ({len(s.empty_pages)}): {s.empty_pages or '—'}")
        lines.append(f"- short pages ({len(s.short_pages)}): {s.short_pages or '—'}")
        lines.append(
            f"- suspicious pages ({len(s.suspicious_pages)}): {s.suspicious_pages or '—'}"
        )
        lines.append(
            f"- image-only pages ({len(s.image_only_pages)}): {s.image_only_pages or '—'}"
        )
        lines.append("")
    return "\n".join(lines)
