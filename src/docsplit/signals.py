"""Policy loading and signal evaluation.

Engine is type-agnostic: every phrase, pattern, and threshold comes from a
policy YAML (src/docsplit/policies/<type>.yaml). Adding a document type
means adding a policy file, not editing this module.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .normalize import PageText, PhraseMatch, match_phrase, normalize

POLICY_DIR = Path(__file__).parent / "policies"


def load_policy(name: str) -> dict:
    with (POLICY_DIR / f"{name}.yaml").open(encoding="utf-8") as f:
        return yaml.safe_load(f)


@dataclass
class SignalHit:
    signal_id: str
    kind: str  # "decisive" | "supportive"
    method: str
    matched_text: str


@dataclass
class SignalResult:
    decisive: list[SignalHit] = field(default_factory=list)
    supportive: list[SignalHit] = field(default_factory=list)
    excluded_as: str | None = None  # adjacent-document exclusion key (e.g. "scif")
    titles_matched: dict[str, list[str]] = field(default_factory=dict)  # signal_id -> phrases

    def decisive_ids(self) -> list[str]:
        return sorted({h.signal_id for h in self.decisive})

    def supportive_ids(self) -> list[str]:
        return sorted({h.signal_id for h in self.supportive})


def _eval_signal(sig_id: str, spec: dict, page: PageText) -> tuple[list[SignalHit], list[str]]:
    """Returns (hits, matched phrase list). Same-ID repeats collapse to one hit."""
    matched_phrases: list[str] = []
    first: PhraseMatch | None = None
    for phrase in spec.get("phrases", []):
        m = match_phrase(phrase, page)
        if m:
            matched_phrases.append(phrase)
            first = first or m
    for pattern in spec.get("patterns", []):
        m = re.search(pattern, page.fulltext)
        if m:
            matched_phrases.append(m.group(0))
            first = first or PhraseMatch(pattern, "pattern", m.group(0))
    req = spec.get("require_all")
    if req:
        ms = [match_phrase(p, page) for p in req]
        if all(ms):
            matched_phrases.extend(req)
            first = first or ms[0]
        else:
            return [], []
    if first is None:
        return [], []
    return [SignalHit(sig_id, "", first.method, first.matched_text)], matched_phrases


def evaluate_signals(page: PageText, policy: dict) -> SignalResult:
    res = SignalResult()

    for key, spec in policy.get("adjacent_exclusions", {}).items():
        if any(match_phrase(p, page) for p in spec.get("phrases", [])):
            res.excluded_as = key
            return res

    for sig_id, spec in policy.get("decisive", {}).items():
        hits, phrases = _eval_signal(sig_id, spec, page)
        for h in hits:
            h.kind = "decisive"
            res.decisive.append(h)
        if phrases:
            res.titles_matched[sig_id] = phrases

    for sig_id, spec in policy.get("supportive", {}).items():
        hits, phrases = _eval_signal(sig_id, spec, page)
        for h in hits:
            h.kind = "supportive"
            res.supportive.append(h)
        if phrases:
            res.titles_matched[sig_id] = phrases

    return res


def detect_subtype(page: PageText, result: SignalResult, policy: dict) -> tuple[str | None, bool]:
    """Component subtype from footer suffix, else section hints.

    Returns (subtype, conflict). conflict=True means signals disagree and the
    design routes resolution to the LLM (docs/classification/urla.md §3-5).
    """
    sub = policy.get("subtypes", {})
    suffix_hit = None
    for suffix, name in sub.get("suffix_map", {}).items():
        if normalize(suffix) in page.fulltext:
            if suffix_hit and suffix_hit != name:
                return None, True
            suffix_hit = name
    hints = {
        name
        for sig_id, name in sub.get("section_hints", {}).items()
        if any(h.signal_id == sig_id for h in result.supportive)
    }
    if suffix_hit:
        if hints and suffix_hit not in hints:
            return None, True
        return suffix_hit, False
    if len(hints) == 1:
        return next(iter(hints)), False
    if len(hints) > 1:
        return None, True
    if result.decisive:
        return sub.get("default"), False
    return None, False
