"""Combination-rule and ordering tests on synthetic input.

Synthetic pages keep these tests independent of the (uncommitted) dataset: each
test builds the smallest text that should trigger one rule.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from docsplit.cards import SignalCard  # noqa: E402
from docsplit.classify import classify_page  # noqa: E402
from docsplit.grouping import order_instances  # noqa: E402
from docsplit.normalize import PageText  # noqa: E402
from docsplit.signals import detect_subtype, evaluate_signals, load_policy  # noqa: E402

POLICY = {
    "type": "TEST_TYPE",
    "universal": {
        "decisive": {"U-D1": {"layer": "domain", "require_all": ["alpha", "beta"]}},
        "supportive": {
            "U-S1": {"layer": "normative", "phrases": ["gamma"]},
            "U-S2": {"layer": "domain", "phrases": ["delta"]},
            "U-S3": {"layer": "domain", "require_all_any": [["eps"], ["zeta", "eta"]]},
        },
    },
    "vendors": {
        "acme": {
            "identity": {"layer": "vendor", "phrases": ["ACME CORP"]},
            "decisive": {
                "X-D1": {"layer": "vendor", "min_matches": 3,
                         "phrases": ["field one", "field two", "field three", "field four"]}
            },
            "supportive": {"X-S1": {"layer": "vendor", "phrases": ["Report ID:"]}},
            "subtypes": {
                "letter": {"phrases": ["Dear Consumer:"]},
                "summary": {"phrases": ["Client Name:"], "require_absent": ["field one"]},
                "body": {"via": "X-D1", "fallback_if_others": True},
            },
        }
    },
    "adjacent_exclusions": {"other_form": {"phrases": ["Some Other Form 9999"]}},
    "combine": {"decisive_min": 1, "supportive_min": 2,
                "vendor_decisive_requires_identity": True},
}


def grade(text: str, policy: dict = POLICY, competing=None) -> str:
    return classify_page("01", 0, text, policy, competing)[0].grade


# ── combination rule ─────────────────────────────────────────
def test_empty_text_defers_to_vlm():
    assert grade("   \n  ") == "DEFER_VLM"


def test_no_signal():
    assert grade("nothing relevant here") == "NO_SIGNAL"


def test_universal_decisive_is_high():
    assert grade("alpha and beta appear") == "RULE_HIGH"


def test_two_distinct_supportive_is_medium():
    assert grade("gamma and delta") == "RULE_MEDIUM"


def test_single_supportive_defers_to_llm():
    assert grade("only gamma here") == "DEFER_LLM"


def test_same_signal_repeated_counts_once():
    assert grade("gamma gamma gamma") == "DEFER_LLM"


def test_adjacent_exclusion_grade():
    cls = classify_page("01", 0, "Some Other Form 9999 appears", POLICY)[0]
    assert cls.grade == "EXCLUDED_ADJACENT"
    assert cls.flags["excluded_as"] == "other_form"


# ── vendor layer ─────────────────────────────────────────────
def test_vendor_decisive_requires_identity():
    """Without identity the vendor decisive is demoted to a single supportive."""
    text = "field one, field two, field three"
    cls, res, _ = classify_page("01", 0, text, POLICY)
    assert cls.grade == "DEFER_LLM"
    assert res.decisive_ids() == []
    assert res.supportive_ids() == ["X-D1"]
    assert res.supportive[0].demoted_from == "decisive"


def test_vendor_decisive_with_identity_is_high():
    text = "ACME CORP\nfield one, field two, field three"
    cls, res, _ = classify_page("01", 0, text, POLICY)
    assert cls.grade == "RULE_HIGH"
    assert res.identities == ["acme"]
    assert "X-D1" in res.decisive_ids()


def test_min_matches_not_reached():
    text = "ACME CORP\nfield one and field two only"
    cls, res, _ = classify_page("01", 0, text, POLICY)
    assert res.decisive_ids() == []
    assert cls.grade == "NO_SIGNAL"


def test_demoted_vendor_decisive_can_reach_medium_with_another_supportive():
    text = "field one, field two, field three\nReport ID: 123"
    assert grade(text) == "RULE_MEDIUM"


# ── signal spec forms ────────────────────────────────────────
def test_require_all_any_needs_one_per_group():
    # first group satisfied, second group missing -> no match at all
    assert evaluate_signals(PageText.from_raw("eps only"), POLICY).supportive_ids() == []
    # one alternative from each group is enough
    for second in ("zeta", "eta"):
        res = evaluate_signals(PageText.from_raw(f"eps and {second}"), POLICY)
        assert "U-S3" in res.supportive_ids()


def test_require_absent_blocks_match():
    page = PageText.from_raw("Client Name: x\nfield one")
    res = evaluate_signals(page, POLICY)
    sub, _ = detect_subtype(page, res, POLICY)
    assert sub != "summary"


def test_layer_recorded_on_matches():
    cls = classify_page("01", 0, "alpha and beta", POLICY)[0]
    assert {m["layer"] for m in cls.matches} == {"domain"}
    assert cls.signals["layers"] == ["domain"]


# ── subtype resolution ───────────────────────────────────────
def test_specific_subtype_beats_fallback():
    page = PageText.from_raw("ACME CORP\nDear Consumer:\nfield one field two field three")
    res = evaluate_signals(page, POLICY)
    assert detect_subtype(page, res, POLICY)[0] == "letter"


def test_subtype_without_vendor_identity_still_resolves():
    """Score-disclosure-style pages carry the lender letterhead, not the vendor's."""
    page = PageText.from_raw("Dear Consumer:")
    res = evaluate_signals(page, POLICY)
    assert res.identities == []
    assert detect_subtype(page, res, POLICY)[0] == "letter"


# ── type competition ─────────────────────────────────────────
def test_two_types_high_flags_conflict_and_defers():
    rival = {
        "type": "RIVAL_TYPE",
        "universal": {"decisive": {"R-D1": {"layer": "domain", "phrases": ["alpha"]}},
                      "supportive": {}},
        "combine": {"decisive_min": 1, "supportive_min": 2},
    }
    cls = classify_page("01", 0, "alpha and beta", POLICY, [rival])[0]
    assert cls.grade == "DEFER_LLM"
    assert cls.flags["type_conflict"] == ["RIVAL_TYPE", "TEST_TYPE"]


def test_single_type_high_has_no_conflict():
    rival = {
        "type": "RIVAL_TYPE",
        "universal": {"decisive": {"R-D1": {"layer": "domain", "phrases": ["unrelated"]}},
                      "supportive": {}},
        "combine": {"decisive_min": 1, "supportive_min": 2},
    }
    cls = classify_page("01", 0, "alpha and beta", POLICY, [rival])[0]
    assert cls.grade == "RULE_HIGH"
    assert "type_conflict" not in cls.flags


# ── ordering paths ───────────────────────────────────────────
def _card(page: int, subtype=None, markers=(), sections=()):
    return SignalCard(
        package="01", page=page, subtype=subtype,
        page_marker_candidates=[{"n": n, "y": y, "raw": f"{n} of {y}"} for n, y in markers],
        sections_found=list(sections),
    )


def test_ordering_path_a_uses_intact_markers():
    cards = [_card(7, markers=[(2, 3)]), _card(3, markers=[(1, 3)]), _card(9, markers=[(3, 3)])]
    grouping = {"package": "01", "instances": [{"instance_id": "i1", "pages": [7, 3, 9]}]}
    out = order_instances(grouping, cards, {"ordering": {"subtype_order": []}})
    inst = out["instances"][0]
    assert inst["method"] == "CODE_A_PAGE_MARKER"
    assert inst["ordered_pages"] == [3, 7, 9]


def test_ordering_path_a_rejected_when_denominator_mismatches():
    cards = [_card(1, "body", markers=[(1, 11)]), _card(2, "letter", markers=[(2, 11)])]
    grouping = {"package": "01", "instances": [{"instance_id": "i1", "pages": [2, 1]}]}
    policy = {"ordering": {"subtype_order": ["body", "letter"]}}
    inst = order_instances(grouping, cards, policy)["instances"][0]
    assert inst["method"] == "CODE_B_FALLBACK_ORDER"
    assert inst["ordered_pages"] == [1, 2]


def test_ordering_path_b_orders_by_subtype_then_section():
    cards = [
        _card(5, "body", sections=["Section 3: x"]),
        _card(6, "letter"),
        _card(4, "body", sections=["Section 1: y"]),
    ]
    grouping = {"package": "01", "instances": [{"instance_id": "i1", "pages": [6, 5, 4]}]}
    policy = {"ordering": {"subtype_order": ["body", "letter"],
                           "section_rank_pattern": r"section (\d)"}}
    inst = order_instances(grouping, cards, policy)["instances"][0]
    assert inst["ordered_pages"] == [4, 5, 6]


def test_ordering_path_c_marks_unresolved():
    cards = [_card(1, "body", sections=["Section 1: y"]), _card(2)]
    grouping = {"package": "01", "instances": [{"instance_id": "i1", "pages": [1, 2]}]}
    policy = {"ordering": {"subtype_order": ["body"], "section_rank_pattern": r"section (\d)"}}
    inst = order_instances(grouping, cards, policy)["instances"][0]
    assert inst["unresolved"] == [2]
    assert inst["ordered_pages"] == [1]


# ── shipped policies stay loadable and layered ───────────────
@pytest.mark.parametrize("name", ["urla", "credit_report"])
def test_shipped_policy_signals_declare_layer(name):
    policy = load_policy(name)
    groups = []
    uni = policy.get("universal", policy)
    groups += [uni.get("decisive", {}), uni.get("supportive", {})]
    for vblock in (policy.get("vendors") or {}).values():
        groups += [vblock.get("decisive", {}), vblock.get("supportive", {})]
        if vblock.get("identity"):
            groups.append({"identity": vblock["identity"]})
    for group in groups:
        for sig_id, spec in (group or {}).items():
            assert "layer" in spec, f"{name}: {sig_id} 에 layer 없음"


def test_policy_without_vendors_still_evaluates():
    """URLA has no vendor concept; the engine must treat that as normal."""
    policy = load_policy("urla")
    assert "vendors" not in policy
    page = PageText.from_raw("Uniform Residential Loan Application")
    res = evaluate_signals(page, policy)
    assert res.decisive_ids() == ["D1"]
