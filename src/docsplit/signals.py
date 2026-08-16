"""Policy loading and signal evaluation.

The engine is type-agnostic: every phrase, pattern, threshold, and layer comes
from a policy YAML (src/docsplit/policies/<type>.yaml). Adding a document type
means adding a policy file; adding a vendor means adding a block inside one.

Policy shape (docs/classification/credit_report.md §9)::

    universal:            # vendor-independent signals
      decisive:  {ID: {layer: ..., <match spec>}}
      supportive: {...}
    vendors:              # optional; absent for types with no vendor concept
      <key>:
        identity:   {layer: vendor, <match spec>}
        decisive:   {...}
        supportive: {...}
        subtypes:   {name: {<match spec> | via: <signal id>}}

A policy may instead put ``decisive``/``supportive`` at the top level; that is
read as ``universal`` (the URLA policy predates the vendor layer and is not
migrated — see design §9).

Match spec keys, all optional and combinable:

===================  ==========================================================
``phrases``          any listed phrase matches (loose matching)
``patterns``         any regex matches the normalized page text
``min_matches: N``   with ``phrases``: at least N distinct phrases must match
``require_all``      every listed phrase must match
``require_all_any``  list of groups; every group needs >= 1 match
``require_absent``   none of the listed phrases may match
===================  ==========================================================

One flag is not a match rule but changes how a match counts:
``identity_exempt: true`` on a vendor *decisive* signal keeps it decisive even
when that vendor's identity did not match — used for text a standards body
forces onto the page regardless of who issued it (title_report.md §3).

Signal layers (design §2) record *why* a rule is trustworthy:
``normative`` (law/standards body) > ``domain`` (industry structure) >
``vendor`` (one product) > ``deployment`` (per-install; never a rule).
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


def available_policies() -> list[str]:
    return sorted(p.stem for p in POLICY_DIR.glob("*.yaml"))


def universal_block(policy: dict) -> dict:
    """Vendor-independent signals, tolerating the pre-vendor flat layout."""
    if "universal" in policy:
        return policy["universal"]
    return {
        "decisive": policy.get("decisive", {}),
        "supportive": policy.get("supportive", {}),
    }


@dataclass
class SignalHit:
    signal_id: str
    kind: str  # "decisive" | "supportive" | "identity"
    layer: str
    method: str
    matched_text: str
    vendor: str | None = None
    demoted_from: str | None = None  # set when a vendor decisive lacked identity
    identity_exempt: bool = False  # counted as decisive despite no vendor identity

    def to_dict(self) -> dict:
        d = {
            "id": self.signal_id,
            "kind": self.kind,
            "layer": self.layer,
            "method": self.method,
            "text": self.matched_text,
        }
        if self.vendor:
            d["vendor"] = self.vendor
        if self.demoted_from:
            d["demoted_from"] = self.demoted_from
        if self.identity_exempt:
            d["identity_exempt"] = True
        return d


@dataclass
class SignalResult:
    decisive: list[SignalHit] = field(default_factory=list)
    supportive: list[SignalHit] = field(default_factory=list)
    identities: list[str] = field(default_factory=list)  # vendor keys that matched
    excluded_as: str | None = None  # adjacent-document exclusion key (e.g. "scif")
    titles_matched: dict[str, list[str]] = field(default_factory=dict)

    def decisive_ids(self) -> list[str]:
        return sorted({h.signal_id for h in self.decisive})

    def supportive_ids(self) -> list[str]:
        return sorted({h.signal_id for h in self.supportive})

    def all_hits(self) -> list[SignalHit]:
        return self.decisive + self.supportive

    def layers(self) -> list[str]:
        return sorted({h.layer for h in self.all_hits()})


def _eval_spec(spec: dict, page: PageText) -> tuple[PhraseMatch | None, list[str]]:
    """Evaluate one match spec. Returns (representative match, matched phrases)."""
    for phrase in spec.get("require_absent", []):
        if match_phrase(phrase, page):
            return None, []

    matched: list[str] = []
    first: PhraseMatch | None = None

    req = spec.get("require_all")
    if req:
        ms = [match_phrase(p, page) for p in req]
        if not all(ms):
            return None, []
        matched.extend(req)
        first = first or ms[0]

    for group in spec.get("require_all_any", []):
        hit = next((m for m in (match_phrase(p, page) for p in group) if m), None)
        if hit is None:
            return None, []
        matched.append(hit.phrase)
        first = first or hit

    phrases = spec.get("phrases", [])
    if phrases:
        hits = [(p, match_phrase(p, page)) for p in phrases]
        found = [(p, m) for p, m in hits if m]
        need = spec.get("min_matches", 1)
        if len(found) < need:
            return None, []
        matched.extend(p for p, _ in found)
        first = first or found[0][1]

    for pattern in spec.get("patterns", []):
        m = re.search(pattern, page.fulltext)
        if m:
            matched.append(m.group(0))
            first = first or PhraseMatch(pattern, "pattern", m.group(0))

    # A spec with only require_absent (all satisfied) still counts as a match.
    if first is None and spec.get("require_absent") and not (
        phrases or spec.get("patterns") or req or spec.get("require_all_any")
    ):
        first = PhraseMatch("(require_absent)", "absent", "")
    if first is None:
        return None, []
    return first, matched


def _eval_group(
    group: dict, kind: str, page: PageText, res: SignalResult, vendor: str | None = None
) -> list[SignalHit]:
    """Evaluate a dict of {signal_id: spec}; same-ID repeats collapse to one hit."""
    hits = []
    for sig_id, spec in (group or {}).items():
        match, phrases = _eval_spec(spec, page)
        if match is None:
            continue
        hits.append(
            SignalHit(
                signal_id=sig_id,
                kind=kind,
                layer=spec.get("layer", "unspecified"),
                method=match.method,
                matched_text=match.matched_text,
                vendor=vendor,
            )
        )
        if phrases:
            res.titles_matched[sig_id] = phrases
    return hits


def evaluate_signals(page: PageText, policy: dict) -> SignalResult:
    """Evaluate universal signals, then each vendor block, then combine.

    A vendor's decisive signals only count as decisive when that vendor's
    identity also matched (design §4-1); otherwise they are demoted to
    supportive, since the same field names can appear in another vendor's
    report and the correct route is then DEFER_LLM.
    """
    res = SignalResult()

    for key, spec in policy.get("adjacent_exclusions", {}).items():
        if _eval_spec(spec, page)[0]:
            res.excluded_as = key
            return res

    uni = universal_block(policy)
    res.decisive += _eval_group(uni.get("decisive"), "decisive", page, res)
    res.supportive += _eval_group(uni.get("supportive"), "supportive", page, res)

    requires_identity = policy.get("combine", {}).get("vendor_decisive_requires_identity", True)
    for vkey, vblock in (policy.get("vendors") or {}).items():
        identity_spec = vblock.get("identity")
        has_identity = bool(identity_spec) and _eval_spec(identity_spec, page)[0] is not None
        if has_identity:
            res.identities.append(vkey)

        dec_specs = vblock.get("decisive") or {}
        vend_dec = _eval_group(dec_specs, "decisive", page, res, vendor=vkey)
        for h in vend_dec:
            # ``identity_exempt`` marks a signal the association (not the vendor)
            # forces onto the page, so it holds whoever issued the document
            # (title_report.md §3). Everything else needs the vendor's identity.
            exempt = bool(dec_specs.get(h.signal_id, {}).get("identity_exempt"))
            if has_identity or not requires_identity or exempt:
                h.identity_exempt = exempt and not has_identity
                res.decisive.append(h)
            else:  # demote: counts as one supportive ID
                h.kind, h.demoted_from = "supportive", "decisive"
                res.supportive.append(h)
        res.supportive += _eval_group(vblock.get("supportive"), "supportive", page, res, vendor=vkey)

    return res


def evaluate_universal_only(page: PageText, policy: dict) -> SignalResult:
    """Universal signals alone — the vendor-independent coverage probe (C-V5)."""
    stripped = {k: v for k, v in policy.items() if k != "vendors"}
    return evaluate_signals(page, stripped)


def detect_subtype(page: PageText, result: SignalResult, policy: dict) -> tuple[str | None, bool]:
    """Resolve component/package subtype.

    Two policy shapes are supported: footer-suffix + section hints (URLA), and
    per-vendor subtype specs (CREDIT). ``conflict=True`` means signals disagree
    and the design routes resolution to the LLM.
    """
    matched_ids = {h.signal_id for h in result.all_hits()}

    # Subtypes are evaluated even without a vendor identity match: some package
    # members are issued on the lender's letterhead, not the vendor's
    # (credit_report.md §3-3, score_disclosure). Identified vendors go first.
    vendors = policy.get("vendors") or {}
    vendor_order = result.identities + [k for k in vendors if k not in result.identities]
    for vkey in vendor_order:
        subs = vendors.get(vkey, {}).get("subtypes") or {}
        found = set()
        for name, spec in subs.items():
            via = spec.get("via")
            if via is not None:
                if via in matched_ids:
                    found.add(name)
                continue
            if _eval_spec(spec, page)[0] is not None:
                found.add(name)
        # A specific subtype outranks the generic fallback it coexists with.
        fallback = {
            name for name, spec in subs.items() if spec.get("fallback_if_others")
        }
        specific = found - fallback
        if len(specific) == 1:
            return next(iter(specific)), False
        if len(specific) > 1:
            return None, True
        if len(found) == 1:
            return next(iter(found)), False
        if len(found) > 1:
            return None, True

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
        if sig_id in matched_ids
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
