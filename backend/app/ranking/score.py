"""Pure scoring functions for T4 habitat ranking.

No database, network, or file I/O here. All inputs are plain Python dicts/values.

score_investigation(habitat, test_rows) -> InvestigationScore
rank_investigations(habitat, investigations_with_rows) -> list[RankedResult]

Both functions are deterministic: same input always gives the same output.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Data-transfer objects (plain dataclasses — no Pydantic, no IO)
# ---------------------------------------------------------------------------


@dataclass
class InvestigationScore:
    investigation_id: str
    title: str
    acronym: Optional[str]
    score: Optional[float]          # None when tests_total == 0
    match: Optional[float]          # tests_full / tests_total
    coverage: Optional[float]       # rows with both O2 and pressure / tests_total
    tests_total: int
    tests_full: int
    tests_partial: int
    tests_none: int
    unconstrained: List[str]        # dimension names where the habitat bound is None
    note: Optional[str]


# ---------------------------------------------------------------------------
# Single-row classification
# ---------------------------------------------------------------------------


def _classify_row(
    row: Dict[str, Any],
    o2_min: Optional[float],
    o2_max: Optional[float],
    p_min: Optional[float],
    p_max: Optional[float],
) -> str:
    """Return 'full', 'partial', or 'none'."""
    o2 = row.get("oxygen_pct")
    p = row.get("pressure_kpa")

    # Oxygen check
    if o2 is None:
        return "none"

    o2_ok = True
    if o2_min is not None and o2 < o2_min:
        o2_ok = False
    if o2_max is not None and o2 > o2_max:
        o2_ok = False

    if not o2_ok:
        return "none"

    # Pressure check
    if p is None:
        # Oxygen in range but pressure not reported → partial
        return "partial"

    p_ok = True
    if p_min is not None and p < p_min:
        p_ok = False
    if p_max is not None and p > p_max:
        p_ok = False

    return "full" if p_ok else "none"


# ---------------------------------------------------------------------------
# Per-investigation scoring
# ---------------------------------------------------------------------------


def score_investigation(
    investigation_id: str,
    title: str,
    acronym: Optional[str],
    habitat: Dict[str, Any],
    test_rows: List[Dict[str, Any]],
) -> InvestigationScore:
    """Score one investigation against a habitat.

    habitat keys expected (all may be None):
        oxygen_pct_min, oxygen_pct_max, pressure_kpa_min, pressure_kpa_max

    test_rows keys used:
        oxygen_pct (float | None), pressure_kpa (float | None)
    """
    o2_min: Optional[float] = habitat.get("oxygen_pct_min")
    o2_max: Optional[float] = habitat.get("oxygen_pct_max")
    p_min: Optional[float] = habitat.get("pressure_kpa_min")
    p_max: Optional[float] = habitat.get("pressure_kpa_max")

    # Note which dimensions are unconstrained
    unconstrained: List[str] = []
    if o2_min is None and o2_max is None:
        unconstrained.append("oxygen_pct")
    if p_min is None and p_max is None:
        unconstrained.append("pressure_kpa")

    total = len(test_rows)
    if total == 0:
        return InvestigationScore(
            investigation_id=investigation_id,
            title=title,
            acronym=acronym,
            score=None,
            match=None,
            coverage=None,
            tests_total=0,
            tests_full=0,
            tests_partial=0,
            tests_none=0,
            unconstrained=unconstrained,
            note="no test rows in indexed data",
        )

    n_full = n_partial = n_none = 0
    n_both_reported = 0  # rows where both O2 and pressure are non-None

    for row in test_rows:
        cls = _classify_row(row, o2_min, o2_max, p_min, p_max)
        if cls == "full":
            n_full += 1
        elif cls == "partial":
            n_partial += 1
        else:
            n_none += 1

        if row.get("oxygen_pct") is not None and row.get("pressure_kpa") is not None:
            n_both_reported += 1

    score = (n_full + 0.5 * n_partial) / total
    match = n_full / total
    coverage = n_both_reported / total

    return InvestigationScore(
        investigation_id=investigation_id,
        title=title,
        acronym=acronym,
        score=score,
        match=match,
        coverage=coverage,
        tests_total=total,
        tests_full=n_full,
        tests_partial=n_partial,
        tests_none=n_none,
        unconstrained=unconstrained,
        note=None,
    )


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------


def rank_investigations(
    habitat: Dict[str, Any],
    investigations: List[Dict[str, Any]],
    tests_by_investigation: Dict[str, List[Dict[str, Any]]],
) -> List[InvestigationScore]:
    """Score all investigations and return them in ranked order.

    Sort: score descending, then tests_full descending, then investigation_id
    ascending. Investigations with score=None sort last.

    investigations: list of dicts with at least 'id', 'title', 'acronym'
    tests_by_investigation: {investigation_id: [test_row_dict, ...]}
    """
    scores: List[InvestigationScore] = []
    for inv in investigations:
        inv_id = inv["id"]
        rows = tests_by_investigation.get(inv_id, [])
        s = score_investigation(
            investigation_id=inv_id,
            title=inv["title"],
            acronym=inv.get("acronym"),
            habitat=habitat,
            test_rows=rows,
        )
        scores.append(s)

    scores.sort(key=_sort_key)
    return scores


def _sort_key(s: InvestigationScore):
    # None scores sort after all numeric scores
    score_key = (0, -(s.score or 0.0)) if s.score is not None else (1, 0.0)
    return (score_key[0], score_key[1], -(s.tests_full), s.investigation_id)
