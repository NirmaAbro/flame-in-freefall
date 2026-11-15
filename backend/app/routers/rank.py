"""Task T4. Habitat ranking route.

GET /api/v1/rank?habitat=<id>
Returns investigations ranked by how well their test-row conditions match the
habitat's oxygen and pressure ranges, with every part of the score shown.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Response

from .. import fixtures as _fixtures
from .. import data_access
from ..db import get_supabase
from ..ranking.score import InvestigationScore, rank_investigations
from ..schemas import RankResponse, RankedInvestigation, ScorePart

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ranking"])

_FORMULA = (
    "score = (tests_full + 0.5 × tests_partial) / tests_total  "
    "where tests_full = oxygen in range AND pressure in range, "
    "tests_partial = oxygen in range AND pressure not reported"
)

_METHOD_NOTE = (
    "Ranks how closely indexed test conditions match the habitat. "
    "This is not a safety assessment."
)


# ---------------------------------------------------------------------------
# Data loading (Supabase with fixture fallback)
# ---------------------------------------------------------------------------


def _load_from_fixtures():
    """Return (habitats, investigations, tests_by_inv, 'fixtures (sample)')."""
    habs = _fixtures.habitats()
    invs = _fixtures.investigations()
    tests = _fixtures.tests()
    by_inv: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for t in tests:
        by_inv[t["investigation_id"]].append(t)
    return habs, invs, dict(by_inv), "fixtures (sample)"


def _fetch_all_tests_supabase(client) -> List[Dict[str, Any]]:
    """Page through the tests table so more than 1000 rows are never missed."""
    page_size = 1000
    offset = 0
    all_rows: List[Dict[str, Any]] = []
    while True:
        resp = (
            client.table("tests")
            .select("investigation_id, oxygen_pct, pressure_kpa")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        batch = resp.data or []
        all_rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    return all_rows


def _load_from_supabase():
    """Return (habitats, investigations, tests_by_inv, 'supabase').

    Raises DatabaseNotConfigured or any supabase exception on failure.
    """
    client = get_supabase()

    habs = client.table("habitats").select("*").execute().data or []
    invs = (
        client.table("investigations")
        .select("id, title, acronym, source_id")
        .execute()
        .data or []
    )
    tests = _fetch_all_tests_supabase(client)
    by_inv: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for t in tests:
        by_inv[t["investigation_id"]].append(t)

    return habs, invs, dict(by_inv), "supabase"


def _load_data():
    """Load one consistent data source without masking database failures."""
    if not data_access.has_credentials():
        return _load_from_fixtures()

    habs, invs, by_inv, source = _load_from_supabase()
    if not habs:
        raise HTTPException(
            status_code=503,
            detail="Database query returned no habitats.",
        )
    return habs, invs, by_inv, source


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------


@router.get("/rank", response_model=RankResponse)
def rank(habitat: str, response: Response):
    """Rank investigations by test-condition match to the given habitat id."""
    habitats, investigations, tests_by_inv, data_source = _load_data()
    response.headers["X-Data-Source"] = data_source

    found = next((h for h in habitats if h["id"] == habitat), None)
    if found is None:
        raise HTTPException(status_code=404, detail=f'Habitat "{habitat}" was not found.')

    scored: List[InvestigationScore] = rank_investigations(
        habitat=found,
        investigations=investigations,
        tests_by_investigation=tests_by_inv,
    )

    items: List[RankedInvestigation] = []
    for s in scored:
        # Backward-compat: tests_matching maps to full + partial
        tests_matching = (s.tests_full + s.tests_partial) if s.tests_total else None
        parts = [
            ScorePart(name="tests_full", value=s.tests_full),
            ScorePart(name="tests_partial", value=s.tests_partial),
            ScorePart(name="tests_none", value=s.tests_none),
        ]
        items.append(
            RankedInvestigation(
                investigation_id=s.investigation_id,
                title=s.title,
                acronym=s.acronym,
                score=s.score,
                parts=parts,
                match=s.match,
                coverage=s.coverage,
                tests_total=s.tests_total,
                tests_full=s.tests_full,
                tests_partial=s.tests_partial,
                tests_none=s.tests_none,
                unconstrained=s.unconstrained,
                note=s.note,
            )
        )

    return RankResponse(
        habitat=found,
        items=items,
        formula=_FORMULA,
        notes=[],
        data_source=data_source,
        method_note=_METHOD_NOTE,
    )
