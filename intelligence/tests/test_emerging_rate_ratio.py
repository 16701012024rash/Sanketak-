"""Emerging risk must score on rate, not on count.

    PYTHONPATH=. python3 intelligence/tests/test_emerging_rate_ratio.py

The bug being pinned down: `detect_emerging_risks` accepted a baseline and
never read it, so it ranked barrier failures by how often they appeared in the
recent window. The most common failure in the corpus therefore topped the
EMERGING list in almost every window while sitting at its own base rate — an
HSE officer would be pointed at the thing they already know about, while a real
spike ranked below it.

The load-bearing assertion is `test_pair_at_its_base_rate_is_not_emerging`.
A pair running at exactly its historical rate must not be flagged no matter how
large its count is. If that ever passes, the function has gone back to counting.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from intelligence.barrier_drift.emerging_risk import (   # noqa: E402
    detect_emerging_risks,
)

COMMON = ("BAR_POSITIONING", "FM_NOT_COMPLIED")
RARE = ("BAR_ISOLATION_VERIFIED", "FM_NOT_COMPLIED")


def reports(prefix, pairs_per_report):
    """Build reports from a list of per-report barrier-failure pairs."""
    return [
        {
            "report_id": f"{prefix}{i}",
            "barrier_failures": [
                {"barrier": b, "failure_mode": f} for b, f in pairs
            ],
        }
        for i, pairs in enumerate(pairs_per_report)
    ]


def flagged(risks):
    return {(r["barrier"], r["failure_mode"]) for r in risks}


def ratio_of(risks, pair):
    for r in risks:
        if (r["barrier"], r["failure_mode"]) == pair:
            return r["rate_ratio"]
    return None


# --------------------------------------------------------------------------
# THE regression: base rate is not emergence
# --------------------------------------------------------------------------

def test_pair_at_its_base_rate_is_not_emerging():
    """50% of the baseline, 50% of the window -> ratio 1.0 -> not emerging.

    COMMON is by far the highest count in the recent window (5 occurrences,
    more than everything else combined). The old implementation ranked it
    first. It is running at exactly its historical rate, so it is not a
    finding.
    """
    baseline = reports("H", [[COMMON], [COMMON], [RARE], [("BAR_X", "FM_ABSENT")]] * 25)
    recent = reports("R", [[COMMON], [COMMON], [RARE], [("BAR_X", "FM_ABSENT")]] * 2
                     + [[COMMON]])

    risks = detect_emerging_risks(baseline + recent, recent)

    assert COMMON not in flagged(risks), (
        f"a pair at its base rate was flagged as EMERGING: {risks}. "
        f"This is the original bug — scoring has reverted to raw counts."
    )


def test_the_highest_count_is_not_automatically_first():
    """Ranking is by rate ratio; a lower-count spike outranks a common pair."""
    baseline = reports("H", [[COMMON]] * 60 + [[RARE]] * 2)
    # COMMON slightly up, RARE sharply up.
    recent = reports("R", [[COMMON]] * 6 + [[RARE]] * 3)

    risks = detect_emerging_risks(baseline + recent, recent)

    assert risks, "a genuine spike should be flagged"
    assert (risks[0]["barrier"], risks[0]["failure_mode"]) == RARE
    assert risks[0]["recent_occurrences"] < 6   # ranked above a larger count


def test_a_genuine_spike_is_flagged():
    baseline = reports("H", [[COMMON]] * 50 + [[RARE]] * 2)
    recent = reports("R", [[RARE]] * 4 + [[COMMON]] * 2)

    risks = detect_emerging_risks(baseline + recent, recent)

    assert RARE in flagged(risks)
    assert ratio_of(risks, RARE) > 1.5


# --------------------------------------------------------------------------
# the two gates
# --------------------------------------------------------------------------

def test_a_single_occurrence_cannot_spike():
    """One occurrence of a never-seen pair has a huge ratio and no evidence."""
    baseline = reports("H", [[COMMON]] * 50)
    recent = reports("R", [[("BAR_NEW", "FM_ABSENT")]] + [[COMMON]] * 5)

    risks = detect_emerging_risks(baseline + recent, recent)

    assert ("BAR_NEW", "FM_ABSENT") not in flagged(risks)


def test_a_repeated_new_pair_is_flagged():
    """Two occurrences of a pair with no history is the clearest emergence."""
    baseline = reports("H", [[COMMON]] * 50)
    recent = reports("R", [[("BAR_NEW", "FM_ABSENT")]] * 2 + [[COMMON]] * 5)

    risks = detect_emerging_risks(baseline + recent, recent)

    assert ("BAR_NEW", "FM_ABSENT") in flagged(risks)


def test_ratio_gate_is_enforced():
    """A pair only slightly above its base rate does not clear 1.5."""
    baseline = reports("H", [[COMMON]] * 40 + [[RARE]] * 10)
    recent = reports("R", [[COMMON]] * 8 + [[RARE]] * 3)   # RARE 20% vs 20%

    risks = detect_emerging_risks(baseline + recent, recent)
    assert RARE not in flagged(risks)


# --------------------------------------------------------------------------
# the baseline parameter is actually read
# --------------------------------------------------------------------------

def test_baseline_is_used_at_all():
    """Same recent window, different history -> different answer.

    If the baseline is ignored again, these two calls return the same thing.
    """
    recent = reports("R", [[RARE]] * 3)

    seen_before = reports("H", [[RARE]] * 50)
    never_seen = reports("H", [[COMMON]] * 50)

    a = detect_emerging_risks(seen_before + recent, recent)
    b = detect_emerging_risks(never_seen + recent, recent)

    assert flagged(a) != flagged(b), (
        "the historical baseline is not being read — this was the bug"
    )
    assert RARE not in flagged(a)   # always been the only failure: normal
    assert RARE in flagged(b)       # never seen before: emerging


def test_recent_reports_are_excluded_from_their_own_baseline():
    """The window must not dilute the baseline it is measured against."""
    recent = reports("R", [[RARE]] * 3)
    baseline = reports("H", [[COMMON]] * 20)

    with_overlap = detect_emerging_risks(baseline + recent, recent)
    assert RARE in flagged(with_overlap)


def test_no_baseline_flags_nothing():
    """Nothing to compare against is not a licence to flag everything."""
    recent = reports("R", [[RARE]] * 5)
    assert detect_emerging_risks([], recent) == []
    assert detect_emerging_risks(recent, recent) == []


def test_empty_window_is_empty():
    assert detect_emerging_risks(reports("H", [[COMMON]] * 10), []) == []


# --------------------------------------------------------------------------
# against the real corpus
# --------------------------------------------------------------------------

def test_real_corpus_does_not_flag_the_most_common_pair():
    """BAR_POSITIONING/FM_NOT_COMPLIED topped every window under the old code.

    It is the most frequent failure in the corpus (64/305) and sits at its own
    base rate in the recent window. It must not be called emerging.
    """
    from intelligence.data.report_repository import load_historical_reports

    corpus = load_historical_reports()
    for window in (50, 100):
        risks = detect_emerging_risks(corpus, corpus[-window:])
        assert COMMON not in flagged(risks), (
            f"window={window}: the corpus's most common failure was flagged "
            f"as EMERGING at its own base rate"
        )


if __name__ == "__main__":
    import logging
    logging.disable(logging.WARNING)
    passed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
            passed += 1
    print(f"\n{passed} passed — base rate is not emergence")
