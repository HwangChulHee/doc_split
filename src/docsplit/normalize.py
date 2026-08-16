"""Text normalization and loose phrase matching.

Promoted from scripts/observe_urla_diff.py. Matching order follows the
design doc (docs/classification/urla.md §3-4):
    exact line -> substring of rejoined full text -> fuzzy (0.90)
Rationale for loose matching: byte-level equality breaks even between the
two GSE publications of the same form (docs/analysis/urla_standard_analysis.md §7, §10).
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from dataclasses import dataclass

FUZZY_CUTOFF = 0.90


def normalize(text: str) -> str:
    s = unicodedata.normalize("NFKC", text)
    s = s.replace("•", "·").replace("●", "·")
    s = s.replace("—", "-").replace("–", "-")
    # NFKC leaves curly quotes alone, so a reference printing Employee's with
    # U+2019 never matches a document printing it with U+0027
    # (income_standard_analysis.md §3-4).
    s = s.replace("‘", "'").replace("’", "'")
    s = s.replace("“", '"').replace("”", '"')
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


@dataclass
class PageText:
    """Normalized views of one page's raw text, built once and reused."""

    raw: str
    lines: list[str]  # normalized non-empty lines
    fulltext: str  # normalized lines rejoined with single spaces

    @classmethod
    def from_raw(cls, raw: str) -> "PageText":
        lines = [normalize(l) for l in raw.splitlines()]
        lines = [l for l in lines if l]
        return cls(raw=raw, lines=lines, fulltext=" ".join(lines))


@dataclass
class PhraseMatch:
    phrase: str
    method: str  # "line" | "substring" | "fuzzy"
    matched_text: str


def match_phrase(phrase: str, page: PageText) -> PhraseMatch | None:
    """Loose match of a representative phrase against a page."""
    p = normalize(phrase)
    if p in page.lines:
        return PhraseMatch(phrase, "line", p)
    if p in page.fulltext:
        return PhraseMatch(phrase, "substring", p)
    near = difflib.get_close_matches(p, page.lines, n=1, cutoff=FUZZY_CUTOFF)
    if near:
        return PhraseMatch(phrase, "fuzzy", near[0])
    return None
