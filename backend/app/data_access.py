"""Shared data-access layer for T3 routes (investigations, tests, habitats, export).

Design
------
- has_credentials(): True when both SUPABASE_URL and SUPABASE_KEY are set.
- Credentials MISSING  → serve fixtures from backend/fixtures/, return
  X-Data-Source: fixtures (sample).
- Credentials PRESENT  → query Supabase, return X-Data-Source: supabase.
  If Supabase raises, propagate HTTP 503. Never silently fall back to fixtures
  when credentials are present, so fake data is never shown as real.
- All filtering, ordering and pagination is done in the database.
- For CSV exports, the table is paged in chunks so nothing is cut off.

Public symbols
--------------
has_credentials() -> bool
DATA_SOURCE_FIXTURE = "fixtures (sample)"
DATA_SOURCE_SUPABASE = "supabase"


Investigations
  list_investigations(q, hardware_family, page, page_size) -> (rows, total, source)
  get_investigation(inv_id) -> (row_or_None, source)

Tests
  list_tests(investigation_id, fuel, outcome,
             min_oxygen, max_oxygen, min_pressure_kpa, max_pressure_kpa,
             page, page_size) -> (rows, total, source)
  get_test(test_id) -> (row_or_None, source)
  iter_tests_csv(investigation_id) -> Iterator[dict]

Habitats
  list_habitats() -> (rows, source)
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Auto-load backend/.env so that `python -c "from app.main import app; ..."`
# picks up credentials even when the shell has not exported them.
# python-dotenv is in requirements.txt; override=False so a real env var always wins.
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv as _load_dotenv
    _ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
    if _ENV_PATH.exists():
        _load_dotenv(dotenv_path=_ENV_PATH, override=False)
except ImportError:
    pass  # python-dotenv not installed; env vars must come from the shell

from .config import get_settings
from . import fixtures as _fixtures

DATA_SOURCE_FIXTURE = "fixtures (sample)"
DATA_SOURCE_SUPABASE = "supabase"
CSV_PAGE_SIZE = 1000


# ---------------------------------------------------------------------------
# Credential check
# ---------------------------------------------------------------------------

def has_credentials() -> bool:
    """Return True when Supabase URL and key are both non-empty."""
    s = get_settings()
    return bool(s.supabase_url and s.supabase_key)


def _get_client():
    """Return a live Supabase client. Assumes has_credentials() is True."""
    from .db import get_supabase
    return get_supabase()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_COMMA_PAREN = re.compile(r"[,()\[\]]")


def _sanitize_q(q: Optional[str]) -> Optional[str]:
    """Strip commas and parentheses from q to prevent filter injection."""
    if q is None:
        return None
    cleaned = _COMMA_PAREN.sub(" ", q).strip()
    return cleaned or None


def _sanitize_lookup(value: str) -> str:
    """Keep lookup values safe for Supabase's PostgREST filter expression."""
    return re.sub(r"[,()]", " ", value).strip()


_SUPABASE_ALIASES = {
    "psi-bass-ii": "PSI-25",
    "psi-bass": "PSI-26",
    "psi-flex": "PSI-69",
    "psi-flex-2": "PSI-68",
}

_FIXTURE_ALIASES = {
    "psi-25": "psi-bass-ii",
    "psi-26": "psi-bass",
    "psi-69": "psi-flex",
    "psi-68": "psi-flex-2",
}


def _fixture_investigation(inv_id: str) -> Optional[Dict[str, Any]]:
    """Find a fixture record by canonical id, source id, acronym, or alias."""
    wanted = inv_id.casefold()
    target_fixture_id = _FIXTURE_ALIASES.get(wanted)
    for rec in _fixtures.investigations():
        rec_id = str(rec.get("id") or "").casefold()
        if target_fixture_id and rec_id == target_fixture_id:
            return rec
        if wanted in {
            rec_id,
            str(rec.get("source_id") or "").casefold(),
            str(rec.get("acronym") or "").casefold(),
        }:
            return rec
    return None


def _supabase_investigation_query(client, inv_id: str):
    """Build a case-insensitive lookup across id, source_id, and acronym."""
    lookup = _sanitize_lookup(inv_id)
    alias = _SUPABASE_ALIASES.get(inv_id.casefold())
    table = client.table("investigations").select(
        "id, source_id, title, acronym, summary, research_area, project_type, "
        "platform, environment, hardware, fuel_classes, fuel_materials, "
        "topic_tags, measurement_types, conditions, files, publications, "
        "source_url, doi, source_updated_at, ingested_at, data_status"
    )
    if alias:
        return table.or_(
            f"id.ilike.{lookup},source_id.ilike.{lookup},acronym.ilike.{lookup},"
            f"id.ilike.{alias},source_id.ilike.{alias},acronym.ilike.{alias}"
        )
    return table.or_(
        f"id.ilike.{lookup},source_id.ilike.{lookup},acronym.ilike.{lookup}"
    )


def _canonical_investigation_id(inv_id: str) -> Optional[str]:
    """Resolve an investigation alias to the stored canonical id."""
    if not has_credentials():
        record = _fixture_investigation(inv_id)
        return record.get("id") if record else None

    direct_alias = _SUPABASE_ALIASES.get(inv_id.casefold())
    if direct_alias:
        return direct_alias

    client = _get_client()
    table = client.table("investigations")
    query = table.select(
        "id, source_id, title, acronym, summary, research_area, project_type, "
        "platform, environment, hardware, fuel_classes, fuel_materials, "
        "topic_tags, measurement_types, conditions, files, publications, "
        "source_url, doi, source_updated_at, ingested_at, data_status"
    )
    if not hasattr(query, "or_"):
        for field in ("id", "source_id", "acronym"):
            try:
                candidate = client.table("investigations").select(
                    "id, source_id, acronym"
                ).eq(field, inv_id).execute()
            except Exception as exc:
                _supabase_503(exc)
            rows = candidate.data or []
            for row in rows:
                if inv_id.casefold() in {
                    str(row.get("id") or "").casefold(),
                    str(row.get("source_id") or "").casefold(),
                    str(row.get("acronym") or "").casefold(),
                }:
                    return row.get("id") or inv_id
        return inv_id

    try:
        response = _supabase_investigation_query(client, inv_id).execute()
    except Exception as exc:
        _supabase_503(exc)
    rows = response.data or []
    return rows[0].get("id") if rows else inv_id


def _supabase_503(exc: Exception):
    """Raise HTTP 503 when a Supabase call fails."""
    from fastapi import HTTPException
    raise HTTPException(
        status_code=503,
        detail=f"Database query failed: {exc}",
    )


# ---------------------------------------------------------------------------
# Investigations
# ---------------------------------------------------------------------------

def list_investigations(
    q: Optional[str] = None,
    hardware_family: Optional[str] = None,
    page: int = 1,
    page_size: int = 25,
) -> Tuple[List[Dict[str, Any]], int, str]:
    """Return (rows, total, data_source)."""
    if not has_credentials():
        rows = _list_investigations_fixture(q, hardware_family, page, page_size)
        total = _count_investigations_fixture(q, hardware_family)
        return rows, total, DATA_SOURCE_FIXTURE

    # --- Supabase path ---
    try:
        client = _get_client()
        query = client.table("investigations").select(
            "id, source_id, title, acronym, summary, research_area, project_type, "
            "platform, environment, hardware, fuel_classes, fuel_materials, "
            "topic_tags, measurement_types, conditions, files, publications, "
            "source_url, doi, source_updated_at, ingested_at, data_status",
            count="exact",
        ).order("id")

        q_clean = _sanitize_q(q)
        if q_clean:
            # ilike is case-insensitive; we search several text columns
            query = query.or_(
                f"title.ilike.%{q_clean}%,"
                f"acronym.ilike.%{q_clean}%,"
                f"summary.ilike.%{q_clean}%,"
                f"source_id.ilike.%{q_clean}%"
            )
        if hardware_family:
            query = query.ilike("hardware", f"%{hardware_family}%")

        offset = (page - 1) * page_size
        resp = query.range(offset, offset + page_size - 1).execute()
    except Exception as exc:
        _supabase_503(exc)

    rows = resp.data or []
    total = resp.count if resp.count is not None else len(rows)
    return rows, total, DATA_SOURCE_SUPABASE


def _list_investigations_fixture(
    q: Optional[str],
    hardware_family: Optional[str],
    page: int,
    page_size: int,
) -> List[Dict[str, Any]]:
    rows = _filter_investigations_fixture(q, hardware_family)
    start = (page - 1) * page_size
    return rows[start : start + page_size]


def _count_investigations_fixture(
    q: Optional[str],
    hardware_family: Optional[str],
) -> int:
    return len(_filter_investigations_fixture(q, hardware_family))


def _filter_investigations_fixture(
    q: Optional[str],
    hardware_family: Optional[str],
) -> List[Dict[str, Any]]:
    rows = list(_fixtures.investigations())
    q_clean = _sanitize_q(q)
    if q_clean:
        q_lower = q_clean.lower()
        rows = [
            r for r in rows
            if q_lower in (r.get("title") or "").lower()
            or q_lower in (r.get("acronym") or "").lower()
            or q_lower in (r.get("summary") or "").lower()
            or q_lower in (r.get("source_id") or "").lower()
            or q_lower in (r.get("hardware") or "").lower()
        ]
    if hardware_family:
        hf_lower = hardware_family.lower()
        rows = [
            r for r in rows
            if hf_lower in (r.get("hardware") or "").lower()
        ]
    rows.sort(key=lambda r: r["id"])
    return rows


def get_investigation(inv_id: str) -> Tuple[Optional[Dict[str, Any]], str]:
    """Return (row_or_None, data_source)."""
    if not has_credentials():
        return _fixture_investigation(inv_id), DATA_SOURCE_FIXTURE

    try:
        resp = _supabase_investigation_query(_get_client(), inv_id).execute()
    except Exception as exc:
        _supabase_503(exc)

    rows = resp.data or []
    return (rows[0] if rows else None), DATA_SOURCE_SUPABASE


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def list_tests(
    investigation_id: Optional[str] = None,
    fuel: Optional[str] = None,
    outcome: Optional[str] = None,
    min_oxygen: Optional[float] = None,
    max_oxygen: Optional[float] = None,
    min_pressure_kpa: Optional[float] = None,
    max_pressure_kpa: Optional[float] = None,
    page: int = 1,
    page_size: int = 50,
) -> Tuple[List[Dict[str, Any]], int, str]:
    """Return (rows, total, data_source)."""
    if not has_credentials():
        canonical_id = _canonical_investigation_id(investigation_id) if investigation_id else None
        if investigation_id and canonical_id is None:
            return [], 0, DATA_SOURCE_FIXTURE
        rows = _filter_tests_fixture(
            canonical_id, fuel, outcome,
            min_oxygen, max_oxygen, min_pressure_kpa, max_pressure_kpa,
        )
        start = (page - 1) * page_size
        return rows[start : start + page_size], len(rows), DATA_SOURCE_FIXTURE

    try:
        client = _get_client()
        query = (
            client.table("tests")
            .select("*", count="exact")
            .order("investigation_id")
            .order("source_row")
        )
        if investigation_id:
            canonical_id = _canonical_investigation_id(investigation_id)
            if canonical_id is None:
                return [], 0, DATA_SOURCE_SUPABASE
            query = query.eq("investigation_id", canonical_id)
        if fuel:
            query = query.ilike("fuel", f"%{fuel}%")
        if outcome:
            query = query.ilike("outcome", f"%{outcome}%")
        # Numeric range filters: a row with NULL is excluded when the filter is active
        if min_oxygen is not None:
            query = query.gte("oxygen_pct", min_oxygen)
        if max_oxygen is not None:
            query = query.lte("oxygen_pct", max_oxygen)
        if min_pressure_kpa is not None:
            query = query.gte("pressure_kpa", min_pressure_kpa)
        if max_pressure_kpa is not None:
            query = query.lte("pressure_kpa", max_pressure_kpa)

        offset = (page - 1) * page_size
        resp = query.range(offset, offset + page_size - 1).execute()
    except Exception as exc:
        _supabase_503(exc)

    rows = resp.data or []
    total = resp.count if resp.count is not None else len(rows)
    return rows, total, DATA_SOURCE_SUPABASE


def _filter_tests_fixture(
    investigation_id: Optional[str],
    fuel: Optional[str],
    outcome: Optional[str],
    min_oxygen: Optional[float],
    max_oxygen: Optional[float],
    min_pressure_kpa: Optional[float],
    max_pressure_kpa: Optional[float],
) -> List[Dict[str, Any]]:
    rows = list(_fixtures.tests())
    if investigation_id:
        rows = [r for r in rows if r.get("investigation_id") == investigation_id]
    if fuel:
        fl = fuel.lower()
        rows = [r for r in rows if fl in (r.get("fuel") or "").lower()]
    if outcome:
        ol = outcome.lower()
        rows = [r for r in rows if ol in (r.get("outcome") or "").lower()]
    if min_oxygen is not None:
        rows = [r for r in rows if r.get("oxygen_pct") is not None and r["oxygen_pct"] >= min_oxygen]
    if max_oxygen is not None:
        rows = [r for r in rows if r.get("oxygen_pct") is not None and r["oxygen_pct"] <= max_oxygen]
    if min_pressure_kpa is not None:
        rows = [r for r in rows if r.get("pressure_kpa") is not None and r["pressure_kpa"] >= min_pressure_kpa]
    if max_pressure_kpa is not None:
        rows = [r for r in rows if r.get("pressure_kpa") is not None and r["pressure_kpa"] <= max_pressure_kpa]
    # Order by investigation_id then source_row
    rows.sort(key=lambda r: (r.get("investigation_id") or "", r.get("source_row") or 0))
    return rows


def get_test(test_id: str) -> Tuple[Optional[Dict[str, Any]], str]:
    """Return (row_or_None, data_source)."""
    if not has_credentials():
        for row in _fixtures.tests():
            if row["id"] == test_id:
                return row, DATA_SOURCE_FIXTURE
        return None, DATA_SOURCE_FIXTURE

    try:
        client = _get_client()
        resp = (
            client.table("tests")
            .select("*")
            .eq("id", test_id)
            .single()
            .execute()
        )
    except Exception as exc:
        msg = str(exc).lower()
        if "0 rows" in msg or "no rows" in msg or "jsondecodeerror" in msg or "pgrst116" in msg:
            return None, DATA_SOURCE_SUPABASE
        _supabase_503(exc)

    return resp.data, DATA_SOURCE_SUPABASE


def iter_tests_csv(
    investigation_id: Optional[str] = None,
) -> Tuple[Iterator[Dict[str, Any]], str]:
    """Return (iterator_of_rows, data_source).

    When credentials are present the table is paged in chunks of 1000.
    """
    canonical_id = _canonical_investigation_id(investigation_id) if investigation_id else None
    if investigation_id and canonical_id is None:
        return iter([]), (DATA_SOURCE_SUPABASE if has_credentials() else DATA_SOURCE_FIXTURE)

    if not has_credentials():
        rows = _filter_tests_fixture(canonical_id, None, None, None, None, None, None)
        return iter(rows), DATA_SOURCE_FIXTURE

    def _iter_supabase():
        client = _get_client()
        offset = 0
        while True:
            try:
                query = (
                    client.table("tests")
                    .select("*")
                    .order("investigation_id")
                    .order("source_row")
                )
                if canonical_id:
                    query = query.eq("investigation_id", canonical_id)
                resp = query.range(offset, offset + CSV_PAGE_SIZE - 1).execute()
                batch = resp.data or []
            except Exception as exc:
                _supabase_503(exc)

            if not batch:
                break
            yield from batch
            if len(batch) < CSV_PAGE_SIZE:
                break
            offset += len(batch)

    return _iter_supabase(), DATA_SOURCE_SUPABASE


# ---------------------------------------------------------------------------
# Habitats
# ---------------------------------------------------------------------------

def list_habitats() -> Tuple[List[Dict[str, Any]], str]:
    """Return (rows, data_source)."""
    if not has_credentials():
        return list(_fixtures.habitats()), DATA_SOURCE_FIXTURE

    try:
        client = _get_client()
        resp = (
            client.table("habitats")
            .select("*")
            .order("id")
            .execute()
        )
    except Exception as exc:
        _supabase_503(exc)

    rows = resp.data or []
    # If the habitats table is empty, fall back to fixtures so dev mode still works
    if not rows:
        return list(_fixtures.habitats()), DATA_SOURCE_FIXTURE
    return rows, DATA_SOURCE_SUPABASE
