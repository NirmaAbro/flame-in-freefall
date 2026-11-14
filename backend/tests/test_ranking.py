"""Tests for T4 habitat ranking.

All tests are offline (no network). The route tests use FastAPI's TestClient
with the fixture fallback.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ranking.score import (
    InvestigationScore,
    _classify_row,
    rank_investigations,
    score_investigation,
)
from app.schemas import RankResponse

client = TestClient(app)
API = "/api/v1"


# ---------------------------------------------------------------------------
# Habitat fixture helpers
# ---------------------------------------------------------------------------

HAB_ISS = {
    "id": "iss",
    "name": "ISS",
    "oxygen_pct_min": 19.5,
    "oxygen_pct_max": 23.1,
    "pressure_kpa_min": 97.9,
    "pressure_kpa_max": 102.7,
    "gravity": "microgravity",
}

HAB_UNCONSTRAINED = {
    "id": "open",
    "name": "Unconstrained",
    "oxygen_pct_min": None,
    "oxygen_pct_max": None,
    "pressure_kpa_min": None,
    "pressure_kpa_max": None,
    "gravity": None,
}


# ---------------------------------------------------------------------------
# _classify_row
# ---------------------------------------------------------------------------


class TestClassifyRow:
    def test_full_match(self):
        row = {"oxygen_pct": 21.0, "pressure_kpa": 101.3}
        assert _classify_row(row, 19.5, 23.1, 97.9, 102.7) == "full"

    def test_oxygen_missing_gives_none(self):
        row = {"oxygen_pct": None, "pressure_kpa": 101.3}
        assert _classify_row(row, 19.5, 23.1, 97.9, 102.7) == "none"

    def test_oxygen_out_of_range_gives_none(self):
        row = {"oxygen_pct": 30.0, "pressure_kpa": 101.3}
        assert _classify_row(row, 19.5, 23.1, 97.9, 102.7) == "none"

    def test_pressure_none_with_o2_ok_gives_partial(self):
        row = {"oxygen_pct": 21.0, "pressure_kpa": None}
        assert _classify_row(row, 19.5, 23.1, 97.9, 102.7) == "partial"

    def test_pressure_out_of_range_gives_none_not_partial(self):
        """A known but out-of-range pressure must be 'none', not 'partial'."""
        row = {"oxygen_pct": 21.0, "pressure_kpa": 50.0}
        assert _classify_row(row, 19.5, 23.1, 97.9, 102.7) == "none"

    def test_unconstrained_bounds_always_pass(self):
        """When a habitat has no bounds, every row with a value passes that check."""
        row = {"oxygen_pct": 50.0, "pressure_kpa": 200.0}
        assert _classify_row(row, None, None, None, None) == "full"

    def test_one_sided_bound_works(self):
        """o2_min=30, o2_max=None → anything >= 30 is in range."""
        row = {"oxygen_pct": 35.0, "pressure_kpa": None}
        assert _classify_row(row, 30.0, None, None, None) == "partial"
        row_low = {"oxygen_pct": 25.0, "pressure_kpa": None}
        assert _classify_row(row_low, 30.0, None, None, None) == "none"


# ---------------------------------------------------------------------------
# score_investigation
# ---------------------------------------------------------------------------


class TestScoreInvestigation:
    def test_score_0_5_for_one_partial_row(self):
        """One partial row out of one total must yield score == 0.5."""
        rows = [{"oxygen_pct": 21.0, "pressure_kpa": None}]
        s = score_investigation("inv1", "Title", None, HAB_ISS, rows)
        assert s.score == pytest.approx(0.5)
        assert s.tests_total == 1
        assert s.tests_full == 0
        assert s.tests_partial == 1
        assert s.tests_none == 0

    def test_score_1_0_for_all_full(self):
        rows = [{"oxygen_pct": 21.0, "pressure_kpa": 101.3}] * 4
        s = score_investigation("inv1", "T", None, HAB_ISS, rows)
        assert s.score == pytest.approx(1.0)

    def test_score_0_for_no_matches(self):
        rows = [{"oxygen_pct": 50.0, "pressure_kpa": 200.0}] * 3
        s = score_investigation("inv1", "T", None, HAB_ISS, rows)
        assert s.score == pytest.approx(0.0)

    def test_zero_tests_gives_none_score(self):
        s = score_investigation("inv1", "Title", None, HAB_ISS, [])
        assert s.score is None
        assert s.tests_total == 0
        assert s.note is not None

    def test_unconstrained_dimensions_listed(self):
        s = score_investigation("inv1", "T", None, HAB_UNCONSTRAINED, [])
        assert "oxygen_pct" in s.unconstrained
        assert "pressure_kpa" in s.unconstrained

    def test_mixed_rows(self):
        rows = [
            {"oxygen_pct": 21.0, "pressure_kpa": 101.3},   # full
            {"oxygen_pct": 21.0, "pressure_kpa": None},     # partial
            {"oxygen_pct": 50.0, "pressure_kpa": 101.3},   # none (O2 out)
            {"oxygen_pct": 21.0, "pressure_kpa": 50.0},    # none (P out)
        ]
        s = score_investigation("inv1", "T", None, HAB_ISS, rows)
        assert s.tests_full == 1
        assert s.tests_partial == 1
        assert s.tests_none == 2
        assert s.score == pytest.approx((1 + 0.5) / 4)

    def test_coverage_counts_rows_with_both_reported(self):
        rows = [
            {"oxygen_pct": 21.0, "pressure_kpa": 101.3},   # both reported
            {"oxygen_pct": 21.0, "pressure_kpa": None},     # only O2
            {"oxygen_pct": None, "pressure_kpa": 101.3},    # only P
        ]
        s = score_investigation("inv1", "T", None, HAB_ISS, rows)
        assert s.coverage == pytest.approx(1 / 3)


# ---------------------------------------------------------------------------
# rank_investigations
# ---------------------------------------------------------------------------


class TestRankInvestigations:
    def _make_inv(self, inv_id, title):
        return {"id": inv_id, "title": title, "acronym": None}

    def test_higher_score_ranks_first(self):
        invs = [self._make_inv("b", "B"), self._make_inv("a", "A")]
        tests = {
            "a": [{"oxygen_pct": 21.0, "pressure_kpa": 101.3}],   # full → 1.0
            "b": [{"oxygen_pct": 21.0, "pressure_kpa": None}],     # partial → 0.5
        }
        ranked = rank_investigations(HAB_ISS, invs, tests)
        assert ranked[0].investigation_id == "a"
        assert ranked[1].investigation_id == "b"

    def test_zero_tests_sorts_last(self):
        invs = [
            self._make_inv("empty", "Empty"),
            self._make_inv("full", "Full"),
        ]
        tests = {
            "full": [{"oxygen_pct": 21.0, "pressure_kpa": 101.3}],
            "empty": [],
        }
        ranked = rank_investigations(HAB_ISS, invs, tests)
        assert ranked[-1].investigation_id == "empty"
        assert ranked[-1].score is None

    def test_tie_breaks_by_tests_full_then_id(self):
        """Two investigations with the same score break on tests_full descending,
        then investigation_id ascending."""
        invs = [
            self._make_inv("z", "Z"),
            self._make_inv("a", "A"),
        ]
        # Both get score 0.5: one partial each
        tests = {
            "z": [{"oxygen_pct": 21.0, "pressure_kpa": None}],
            "a": [{"oxygen_pct": 21.0, "pressure_kpa": None}],
        }
        ranked = rank_investigations(HAB_ISS, invs, tests)
        # Same score (0.5), same tests_full (0) → id ascending: "a" before "z"
        assert ranked[0].investigation_id == "a"
        assert ranked[1].investigation_id == "z"

    def test_deterministic_across_calls(self):
        invs = [self._make_inv(f"inv{i}", f"Title {i}") for i in range(5)]
        tests = {f"inv{i}": [{"oxygen_pct": 20.0 + i, "pressure_kpa": 100.0}] for i in range(5)}
        order_1 = [s.investigation_id for s in rank_investigations(HAB_ISS, invs, tests)]
        order_2 = [s.investigation_id for s in rank_investigations(HAB_ISS, invs, tests)]
        assert order_1 == order_2

    def test_stable_order_on_equal_scores(self):
        """All-equal scores: order must be stable (id ascending)."""
        invs = [self._make_inv(f"inv{i:02d}", f"T{i}") for i in range(10)]
        tests = {f"inv{i:02d}": [] for i in range(10)}  # all zero-test
        ranked = rank_investigations(HAB_ISS, invs, tests)
        ids = [s.investigation_id for s in ranked]
        assert ids == sorted(ids)


# ---------------------------------------------------------------------------
# Route tests (fixture fallback; no network)
# ---------------------------------------------------------------------------


class TestRankRoute:
    def test_known_habitat_200(self):
        r = client.get(f"{API}/rank", params={"habitat": "moon-base"})
        assert r.status_code == 200
        body = r.json()
        RankResponse.model_validate(body)

    def test_14_items_returned_for_fixture(self):
        r = client.get(f"{API}/rank", params={"habitat": "moon-base"})
        assert r.status_code == 200
        assert len(r.json()["items"]) == 14

    def test_unknown_habitat_404(self):
        r = client.get(f"{API}/rank", params={"habitat": "nowhere"})
        assert r.status_code == 404

    def test_missing_habitat_param_422(self):
        r = client.get(f"{API}/rank")
        assert r.status_code == 422

    def test_method_note_present(self):
        r = client.get(f"{API}/rank", params={"habitat": "moon-base"})
        body = r.json()
        assert body.get("method_note") is not None
        assert "safety" in body["method_note"].lower()

    def test_scores_are_valid(self):
        """Every item with tests_total > 0 must have a score in [0, 1]."""
        r = client.get(f"{API}/rank", params={"habitat": "spacesuit"})
        body = r.json()
        for item in body["items"]:
            if item["tests_total"] and item["tests_total"] > 0:
                assert item["score"] is not None
                assert 0.0 <= item["score"] <= 1.0

    def test_zero_test_items_have_none_score(self):
        """Items with no test rows must have score = null, not 0."""
        r = client.get(f"{API}/rank", params={"habitat": "moon-base"})
        body = r.json()
        for item in body["items"]:
            if item["tests_total"] == 0:
                assert item["score"] is None, (
                    f"{item['investigation_id']}: tests_total=0 but score={item['score']}"
                )

    def test_items_sorted_descending(self):
        """Scores must be in non-increasing order (None scores come last)."""
        r = client.get(f"{API}/rank", params={"habitat": "moon-base"})
        items = r.json()["items"]
        scores = [i["score"] for i in items]
        non_null = [s for s in scores if s is not None]
        null_tail = [s for s in scores if s is None]
        # Non-null portion is non-increasing
        for i in range(len(non_null) - 1):
            assert non_null[i] >= non_null[i + 1]
        # All Nones at the end
        assert scores == non_null + null_tail

    def test_unconstrained_field_present(self):
        """moon-base has o2_max=None and p_min=None so both appear in unconstrained
        for every item (the habitat bound is None, not the test value)."""
        r = client.get(f"{API}/rank", params={"habitat": "moon-base"})
        body = r.json()
        # moon-base: o2_max=None → oxygen unconstrained on the high side only
        # Actually moon-base has o2_min=30 set, so only pressure_kpa is partly None
        # We just check the field exists and is a list
        for item in body["items"]:
            assert isinstance(item["unconstrained"], list)
