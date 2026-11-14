"""Tests for the T3 Read API (investigations, tests, habitats, export).

All tests are offline (no network). The conftest autouse fixture forces
has_credentials() → False so the routes serve fixture data.

The final class TestWithFakeSupabase patches has_credentials() → True and
injects a fake client that always raises, to verify 503 behaviour.
"""
from __future__ import annotations

import csv
import io
import urllib.parse
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app import schemas

client = TestClient(app)
API = "/api/v1"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_ok(path, **params):
    r = client.get(f"{API}{path}", params=params)
    assert r.status_code == 200, f"{r.status_code}: {r.text}"
    return r


def header(response, name: str) -> str:
    return response.headers.get(name, "")


# ---------------------------------------------------------------------------
# Investigations — fixture mode (no credentials)
# ---------------------------------------------------------------------------


class TestInvestigationsFixture:
    def test_list_returns_200_and_validates(self):
        r = get_ok("/investigations")
        schemas.Paginated[schemas.InvestigationListItem].model_validate(r.json())

    def test_data_source_header_is_fixtures(self):
        r = get_ok("/investigations")
        assert header(r, "x-data-source") == "fixtures (sample)"

    def test_pagination_total_matches_fixture_count(self):
        body = get_ok("/investigations", page_size=100).json()
        assert body["total"] == 14  # fixture has 14 records
        assert len(body["items"]) == 14

    def test_page_2_differs_from_page_1(self):
        p1 = get_ok("/investigations", page=1, page_size=5).json()
        p2 = get_ok("/investigations", page=2, page_size=5).json()
        ids1 = {it["id"] for it in p1["items"]}
        ids2 = {it["id"] for it in p2["items"]}
        assert not ids1 & ids2, "Pages must not overlap"

    def test_page_size_over_max_gives_422(self):
        r = client.get(f"{API}/investigations", params={"page_size": 101})
        assert r.status_code == 422

    def test_q_filter_narrows_results(self):
        body_all = get_ok("/investigations", page_size=100).json()
        body_q = get_ok("/investigations", q="bass", page_size=100).json()
        assert body_q["total"] < body_all["total"]
        for item in body_q["items"]:
            text = " ".join([
                item.get("title") or "",
                item.get("acronym") or "",
                item.get("summary") or "",
            ]).lower()
            assert "bass" in text, f"Filter miss: {item['id']}"

    def test_detail_returns_200_and_validates(self):
        r = get_ok("/investigations/psi-bass-ii")
        schemas.Investigation.model_validate(r.json())
        assert header(r, "x-data-source") == "fixtures (sample)"

    def test_detail_unknown_id_gives_404(self):
        r = client.get(f"{API}/investigations/no-such-id")
        assert r.status_code == 404

    def test_items_sorted_by_id(self):
        body = get_ok("/investigations", page_size=100).json()
        ids = [it["id"] for it in body["items"]]
        assert ids == sorted(ids)

    def test_missing_values_are_null_not_empty(self):
        body = get_ok("/investigations/psi-same").json()
        assert body["platform"] is None
        assert body["doi"] is None


# ---------------------------------------------------------------------------
# Tests — fixture mode
# ---------------------------------------------------------------------------


class TestTestsFixture:
    def test_list_returns_paginated(self):
        r = get_ok("/tests")
        body = r.json()
        schemas.Paginated[schemas.TestRow].model_validate(body)
        assert header(r, "x-data-source") == "fixtures (sample)"

    def test_total_matches_fixture_count(self):
        body = get_ok("/tests", page_size=200).json()
        assert body["total"] == 6

    def test_investigation_id_filter(self):
        body = get_ok("/tests", investigation_id="psi-flex", page_size=50).json()
        assert all(r["investigation_id"] == "psi-flex" for r in body["items"])
        assert body["total"] == 3  # 3 psi-flex fixture rows

    def test_fuel_filter_case_insensitive(self):
        body = get_ok("/tests", fuel="methanol", page_size=50).json()
        assert body["total"] > 0
        for row in body["items"]:
            assert "methanol" in (row.get("fuel") or "").lower()

    def test_outcome_filter_case_insensitive(self):
        body = get_ok("/tests", outcome="extinction", page_size=50).json()
        assert body["total"] > 0
        for row in body["items"]:
            assert "extinction" in (row.get("outcome") or "").lower()

    def test_min_oxygen_filter_excludes_null_rows(self):
        # psi-bass-ii rows have oxygen_pct=22.2 and pressure_kpa=null
        # psi-flex rows have oxygen_pct=21.0
        # min_oxygen=22 should return only the bass-ii rows with oxygen >= 22
        body = get_ok("/tests", min_oxygen=22.0, page_size=50).json()
        assert body["total"] > 0
        for row in body["items"]:
            assert row["oxygen_pct"] is not None
            assert row["oxygen_pct"] >= 22.0

    def test_max_oxygen_filter(self):
        body = get_ok("/tests", max_oxygen=21.5, page_size=50).json()
        for row in body["items"]:
            assert row["oxygen_pct"] is not None
            assert row["oxygen_pct"] <= 21.5

    def test_min_pressure_filter_excludes_null_pressure_rows(self):
        # psi-bass-ii rows have pressure_kpa=null; min_pressure must exclude them
        body = get_ok("/tests", min_pressure_kpa=100.0, page_size=50).json()
        for row in body["items"]:
            assert row["pressure_kpa"] is not None
            assert row["pressure_kpa"] >= 100.0

    def test_combined_filters(self):
        # investigation_id + min_oxygen + fuel must all apply (AND)
        body = get_ok(
            "/tests",
            investigation_id="psi-flex",
            min_oxygen=20.0,
            fuel="methanol",
            page_size=50,
        ).json()
        assert body["total"] > 0
        for row in body["items"]:
            assert row["investigation_id"] == "psi-flex"
            assert row["oxygen_pct"] is not None and row["oxygen_pct"] >= 20.0
            assert "methanol" in (row.get("fuel") or "").lower()

    def test_ordered_by_investigation_id_then_source_row(self):
        body = get_ok("/tests", page_size=200).json()
        rows = body["items"]
        for i in range(len(rows) - 1):
            a, b = rows[i], rows[i + 1]
            if a["investigation_id"] == b["investigation_id"]:
                assert (a.get("source_row") or 0) <= (b.get("source_row") or 0)
            else:
                assert a["investigation_id"] <= b["investigation_id"]

    def test_page_size_over_max_gives_422(self):
        r = client.get(f"{API}/tests", params={"page_size": 201})
        assert r.status_code == 422

    def test_pagination_page_2_differs_from_page_1(self):
        p1 = get_ok("/tests", page=1, page_size=3).json()
        p2 = get_ok("/tests", page=2, page_size=3).json()
        ids1 = {r["id"] for r in p1["items"]}
        ids2 = {r["id"] for r in p2["items"]}
        assert not ids1 & ids2

    def test_detail_with_id_containing_space_and_colon(self):
        """IDs like 'PSI-25:file name:1' must be URL-encoded and round-trip correctly."""
        # First get the list to find a fixture id that has colon+space
        # The fixture test id "psi-flex-1" has no special chars — use it for 200
        r = get_ok("/tests/psi-flex-1")
        body = r.json()
        schemas.TestRow.model_validate(body)
        assert body["id"] == "psi-flex-1"
        assert header(r, "x-data-source") == "fixtures (sample)"

    def test_detail_unknown_id_gives_404(self):
        r = client.get(f"{API}/tests/no-such-test")
        assert r.status_code == 404

    def test_all_rows_have_valid_shape(self):
        body = get_ok("/tests", page_size=200).json()
        for row in body["items"]:
            schemas.TestRow.model_validate(row)

    def test_null_pressure_is_none_not_zero(self):
        body = get_ok("/tests", page_size=200).json()
        for row in body["items"]:
            # pressure_kpa must be null or a positive number, never 0
            if row["pressure_kpa"] is not None:
                assert row["pressure_kpa"] > 0, (
                    f"Row {row['id']}: pressure_kpa={row['pressure_kpa']}"
                )


# ---------------------------------------------------------------------------
# Habitats — fixture mode
# ---------------------------------------------------------------------------


class TestHabitatsFixture:
    def test_list_returns_200_and_validates(self):
        r = get_ok("/habitats")
        habitats = r.json()
        assert isinstance(habitats, list)
        for h in habitats:
            schemas.Habitat.model_validate(h)

    def test_data_source_header(self):
        r = get_ok("/habitats")
        assert header(r, "x-data-source") == "fixtures (sample)"

    def test_fixture_habitat_ids_present(self):
        habitats = get_ok("/habitats").json()
        ids = {h["id"] for h in habitats}
        assert "moon-base" in ids
        assert "spacesuit" in ids


# ---------------------------------------------------------------------------
# Export CSV — fixture mode
# ---------------------------------------------------------------------------


class TestExportCSVFixture:
    def test_200_and_content_type(self):
        r = client.get(f"{API}/export/tests.csv")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/csv")

    def test_data_source_header(self):
        r = client.get(f"{API}/export/tests.csv")
        assert header(r, "x-data-source") == "fixtures (sample)"

    def test_header_row_present(self):
        r = client.get(f"{API}/export/tests.csv")
        lines = list(csv.DictReader(io.StringIO(r.text)))
        assert "id" in lines[0]
        assert "pressure_kpa" in lines[0]
        assert "flags" in lines[0]

    def test_null_pressure_is_empty_cell(self):
        r = client.get(f"{API}/export/tests.csv")
        lines = list(csv.DictReader(io.StringIO(r.text)))
        # psi-bass-ii rows have no pressure
        bass_rows = [row for row in lines if row["investigation_id"] == "psi-bass-ii"]
        assert len(bass_rows) > 0
        for row in bass_rows:
            assert row["pressure_kpa"] == "", (
                f"Row {row['id']}: expected empty pressure_kpa, got {row['pressure_kpa']!r}"
            )

    def test_flagged_row_has_non_empty_flags_cell(self):
        r = client.get(f"{API}/export/tests.csv")
        lines = list(csv.DictReader(io.StringIO(r.text)))
        flagged = next((row for row in lines if row["id"] == "psi-bass-ii-b1"), None)
        assert flagged is not None
        assert flagged["flags"] != ""

    def test_unflagged_rows_have_empty_flags_cell(self):
        r = client.get(f"{API}/export/tests.csv")
        lines = list(csv.DictReader(io.StringIO(r.text)))
        unflagged = [row for row in lines if row["id"] != "psi-bass-ii-b1"]
        for row in unflagged:
            assert row["flags"] == "", f"Row {row['id']} has unexpected flags: {row['flags']!r}"

    def test_investigation_id_filter(self):
        r = client.get(f"{API}/export/tests.csv", params={"investigation_id": "psi-flex"})
        assert r.status_code == 200
        lines = list(csv.DictReader(io.StringIO(r.text)))
        assert len(lines) == 3
        assert all(row["investigation_id"] == "psi-flex" for row in lines)

    def test_total_fixture_rows(self):
        r = client.get(f"{API}/export/tests.csv")
        lines = list(csv.DictReader(io.StringIO(r.text)))
        assert len(lines) == 6  # fixture has 6 rows

    def test_content_disposition_attachment(self):
        r = client.get(f"{API}/export/tests.csv")
        cd = r.headers.get("content-disposition", "")
        assert "attachment" in cd
        assert "tests.csv" in cd


# ---------------------------------------------------------------------------
# 503 when credentials present but Supabase raises
# ---------------------------------------------------------------------------


class TestWithFakeSupabase:
    """Verify that when credentials are present and Supabase raises, we get 503,
    not a silent fall-back to fixture data."""

    def _make_failing_client(self):
        """Return a fake Supabase client whose table() always raises."""
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.order.side_effect = (
            RuntimeError("connection refused")
        )
        # chain all query methods to raise
        failing_query = MagicMock()
        failing_query.select.side_effect = RuntimeError("connection refused")
        failing_query.execute.side_effect = RuntimeError("connection refused")
        mock_client.table.return_value = failing_query
        return mock_client

    def test_investigations_503_on_supabase_error(self, monkeypatch):
        import app.data_access as _da
        import app.db as _db
        monkeypatch.setattr(_da, "has_credentials", lambda: True)
        monkeypatch.setattr(_db, "get_supabase", lambda: self._make_failing_client())
        r = client.get(f"{API}/investigations")
        assert r.status_code == 503
        assert "Database query failed" in r.json().get("detail", "")

    def test_tests_503_on_supabase_error(self, monkeypatch):
        import app.data_access as _da
        import app.db as _db
        monkeypatch.setattr(_da, "has_credentials", lambda: True)
        monkeypatch.setattr(_db, "get_supabase", lambda: self._make_failing_client())
        r = client.get(f"{API}/tests")
        assert r.status_code == 503

    def test_habitats_503_on_supabase_error(self, monkeypatch):
        import app.data_access as _da
        import app.db as _db
        monkeypatch.setattr(_da, "has_credentials", lambda: True)
        monkeypatch.setattr(_db, "get_supabase", lambda: self._make_failing_client())
        r = client.get(f"{API}/habitats")
        assert r.status_code == 503

    def test_no_fixture_fallback_when_credentials_present(self, monkeypatch):
        """When credentials are present and Supabase fails, must NOT return 200 fixture data."""
        import app.data_access as _da
        import app.db as _db
        monkeypatch.setattr(_da, "has_credentials", lambda: True)
        monkeypatch.setattr(_db, "get_supabase", lambda: self._make_failing_client())
        r = client.get(f"{API}/investigations")
        # Must not silently serve stale fixture data
        assert r.status_code != 200


# ---------------------------------------------------------------------------
# CSV paging tests — fake Supabase that serves many rows in pages of 1,000
# ---------------------------------------------------------------------------


def _make_paging_client(total_rows: int, investigation_id_filter: str = None):
    """Return a fake Supabase client that serves `total_rows` rows in 1 000-row pages.

    Each row is a minimal dict with an 'id' and 'investigation_id'.
    The client respects .eq("investigation_id", ...) if set.
    """
    # Build the full dataset once
    all_rows = [
        {
            "id": f"INV-1:file.csv:{i + 1}",
            "investigation_id": "INV-1",
            "test_label": str(i + 1),
            "fuel": None,
            "geometry": None,
            "oxygen_pct": None,
            "pressure_kpa": None,
            "flow_cm_s": None,
            "diluent": None,
            "outcome": None,
            "source_file": "file.csv",
            "source_row": i + 1,
            "raw": {},
            "flags": [],
            "data_status": "parsed",
        }
        for i in range(total_rows)
    ]

    class _FakeQuery:
        def __init__(self, rows):
            self._rows = rows
            self._start = 0
            self._end = len(rows) - 1

        def select(self, *a, **kw):
            return self

        def order(self, *a, **kw):
            return self

        def eq(self, field, value):
            if field == "investigation_id":
                self._rows = [r for r in self._rows if r.get(field) == value]
            return self

        def range(self, start, end):
            self._start = start
            self._end = end
            return self

        def execute(self):
            # Supabase range is inclusive on both ends
            batch = self._rows[self._start : self._end + 1]

            class _Resp:
                data = batch

            return _Resp()

    class _FakeTable:
        def __init__(self, rows):
            self._rows = rows

        def select(self, *a, **kw):
            return _FakeQuery(list(self._rows))

    class _FakeClient:
        def table(self, name):
            return _FakeTable(all_rows)

    return _FakeClient()


class TestCSVPaging:
    """Verify the CSV export pages through Supabase correctly for large datasets."""

    def test_2500_rows_all_exported(self, monkeypatch):
        """A fake Supabase with 2 500 rows must produce 2 500 data rows in the CSV."""
        import app.data_access as _da
        import app.db as _db
        fake = _make_paging_client(2500)
        monkeypatch.setattr(_da, "has_credentials", lambda: True)
        monkeypatch.setattr(_db, "get_supabase", lambda: fake)

        r = client.get(f"{API}/export/tests.csv")
        assert r.status_code == 200
        lines = list(csv.DictReader(io.StringIO(r.text)))
        assert len(lines) == 2500, f"Expected 2500 data rows, got {len(lines)}"
        ids = [row["id"] for row in lines]
        assert len(set(ids)) == 2500, "All row ids must be unique (no duplicates)"

    def test_exact_multiple_of_page_size_no_missing_no_duplicates(self, monkeypatch):
        """2 000 rows (exact multiple of 1 000) must not drop or duplicate any row."""
        import app.data_access as _da
        import app.db as _db
        fake = _make_paging_client(2000)
        monkeypatch.setattr(_da, "has_credentials", lambda: True)
        monkeypatch.setattr(_db, "get_supabase", lambda: fake)

        r = client.get(f"{API}/export/tests.csv")
        assert r.status_code == 200
        lines = list(csv.DictReader(io.StringIO(r.text)))
        assert len(lines) == 2000, f"Expected 2000 data rows, got {len(lines)}"
        ids = [row["id"] for row in lines]
        assert len(set(ids)) == 2000, "No duplicate rows"

    def test_investigation_id_filter_with_paging(self, monkeypatch):
        """The investigation_id filter must be passed through to the paging query."""
        import app.data_access as _da
        import app.db as _db
        # Build a dataset where only some rows belong to a target investigation
        total = 1500
        all_rows = [
            {
                "id": f"INV-{'A' if i % 3 == 0 else 'B'}:file.csv:{i + 1}",
                "investigation_id": "INV-A" if i % 3 == 0 else "INV-B",
                "test_label": str(i + 1),
                "fuel": None,
                "geometry": None,
                "oxygen_pct": None,
                "pressure_kpa": None,
                "flow_cm_s": None,
                "diluent": None,
                "outcome": None,
                "source_file": "file.csv",
                "source_row": i + 1,
                "raw": {},
                "flags": [],
                "data_status": "parsed",
            }
            for i in range(total)
        ]
        expected_a = sum(1 for i in range(total) if i % 3 == 0)

        # Use the same _FakeQuery/Client pattern but with our custom rows
        class _FQ:
            def __init__(self, rows):
                self._rows = list(rows)
                self._start = 0
                self._end = len(rows) - 1

            def select(self, *a, **kw): return self
            def order(self, *a, **kw): return self

            def eq(self, field, value):
                if field == "investigation_id":
                    self._rows = [r for r in self._rows if r.get(field) == value]
                return self

            def range(self, start, end):
                self._start = start
                self._end = end
                return self

            def execute(self):
                batch = self._rows[self._start : self._end + 1]
                class _R: data = batch
                return _R()

        class _FT:
            def select(self, *a, **kw): return _FQ(all_rows)

        class _FC:
            def table(self, name): return _FT()

        monkeypatch.setattr(_da, "has_credentials", lambda: True)
        monkeypatch.setattr(_db, "get_supabase", lambda: _FC())

        r = client.get(f"{API}/export/tests.csv", params={"investigation_id": "INV-A"})
        assert r.status_code == 200
        lines = list(csv.DictReader(io.StringIO(r.text)))
        assert len(lines) == expected_a, (
            f"Filter should return {expected_a} rows for INV-A, got {len(lines)}"
        )
        assert all(row["investigation_id"] == "INV-A" for row in lines)

    def test_later_page_failure_is_not_returned_as_a_short_csv(self, monkeypatch):
        """A failure after the first page must be reported instead of truncating output."""
        import app.data_access as _da
        import app.db as _db

        class _FailingQuery:
            def __init__(self):
                self._start = 0

            def select(self, *a, **kw): return self
            def order(self, *a, **kw): return self
            def range(self, start, end):
                self._start = start
                return self

            def execute(self):
                if self._start:
                    raise RuntimeError("connection lost during CSV export")
                return type(
                    "_Response",
                    (),
                    {"data": [{"id": f"row-{i}"} for i in range(1000)]},
                )()

        class _Client:
            def table(self, name):
                return _FailingQuery()

        monkeypatch.setattr(_da, "has_credentials", lambda: True)
        monkeypatch.setattr(_db, "get_supabase", lambda: _Client())

        r = client.get(f"{API}/export/tests.csv")
        assert r.status_code == 503
        assert "Database query failed" in r.json()["detail"]
