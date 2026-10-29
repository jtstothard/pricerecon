"""B1: fixture data can never be presented as a live market fact.

`Comparison.claim()` must either mark a fixture-derived amount `synthetic` on
the envelope (so a caller can refuse it) or, for call sites that demand live
facts (`require_live=True`), exclude fixture paths outright and refuse when
only fixture evidence qualifies.
"""

from datetime import UTC, datetime
from decimal import Decimal

from pricerecon.core.comparisons import claim
from pricerecon.models.assessments import ComparablePath
from pricerecon.models.costs import CostContext

NOW = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)


def path(observation_id: str, amount: str, *, synthetic: bool) -> ComparablePath:
    return ComparablePath(
        candidate_id="candidate",
        capture_id=f"capture:{observation_id}",
        observation_id=observation_id,
        observed_at=NOW,
        amount=Decimal(amount),
        scenario_kind="public_no_coupon",
        offer_key=f"offer:{observation_id}",
        dependencies=[],
        policies={"identity": "watch-identity-v1"},
        valid_until=None,
        evidence_ids=[],
        synthetic=synthetic,
        context=CostContext(),
    )


def test_fixture_winner_is_marked_synthetic_on_the_envelope():
    result = claim([path("obs-1", "45.10", synthetic=True)], "fixture reason")

    assert result.state == "supported"
    assert result.amount == Decimal("45.10")
    assert result.synthetic is True


def test_retained_winner_is_not_marked_synthetic():
    result = claim([path("obs-1", "45.10", synthetic=False)], "retained reason")

    assert result.state == "supported"
    assert result.synthetic is False


def test_dearer_fixture_path_cannot_taint_a_retained_winner():
    result = claim(
        [
            path("obs-live", "45.10", synthetic=False),
            path("obs-fixture", "50.10", synthetic=True),
        ],
        "mixed reason",
    )

    assert result.amount == Decimal("45.10")
    assert result.synthetic is False
    assert result.observation_count == 2
    assert {p.observation_id for p in result.paths} == {"obs-live"}


def test_cheaper_fixture_winner_keeps_the_synthetic_marker():
    result = claim(
        [
            path("obs-live", "50.10", synthetic=False),
            path("obs-fixture", "45.10", synthetic=True),
        ],
        "mixed reason",
    )

    assert result.amount == Decimal("45.10")
    assert result.synthetic is True


def test_live_fact_call_site_refuses_a_fixture_only_candidate_set():
    result = claim([path("obs-1", "45.10", synthetic=True)], "live reason", require_live=True)

    assert result.state == "unavailable"
    assert result.amount is None
    assert result.paths == []
    assert "no live market fact" in result.reason


def test_live_fact_call_site_excludes_fixture_paths_before_computing_the_low():
    result = claim(
        [
            path("obs-live", "45.10", synthetic=False),
            path("obs-fixture", "40.10", synthetic=True),
        ],
        "live reason",
        require_live=True,
    )

    assert result.state == "supported"
    assert result.amount == Decimal("45.10")
    assert result.synthetic is False
    assert {p.observation_id for p in result.paths} == {"obs-live"}


def test_empty_candidate_set_carries_no_amount_and_no_marker():
    result = claim([], "empty reason")

    assert result.state == "unavailable"
    assert result.amount is None
    assert result.synthetic is False
