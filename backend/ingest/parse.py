"""Per-cell parsing logic for PSI Experimental Tables (task T2).

parse_cell(raw_value, field, column, parse_rule, unit) -> (value_or_None, flags)

Rules
-----
- Null tokens (empty string, "N/A", "n/a", "-", "none", "None") → None.
  For a numeric column, also add a flag when the source says "none" explicitly.
- Float parse failure → None + flag.
- Mole-fraction sanity: value > 1 → flag ("value above 1, may already be a percent"),
  do NOT multiply — return as-is after the flag (caller skips unit conversion).
- oxygen_pct outside [0, 100] → flag (keep value).
- pressure_kpa <= 0 → None + flag (physically implausible; raw value kept).
- flow_cm_s negative → flag (keep value).
- BASS-II only extra flags are applied in run.py after a full row is assembled.
"""
from __future__ import annotations

import sys
from typing import Any, List, Optional, Tuple

from .units import convert

# ---------------------------------------------------------------------------
# Null tokens
# ---------------------------------------------------------------------------
_NULL_TOKENS = frozenset({"", "n/a", "na", "-", "none"})


def _is_null(raw: str) -> bool:
    return raw.strip().lower() in _NULL_TOKENS


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_cell(
    raw_value: str,
    field: str,
    column: str,
    parse_rule: str,
    unit: Optional[str],
) -> Tuple[Any, List[str]]:
    """Return (parsed_value_or_None, list_of_flag_strings)."""
    flags: List[str] = []
    stripped = raw_value.strip()

    # ---- Null token check -------------------------------------------------
    if _is_null(stripped):
        if parse_rule == "float" and stripped.lower() == "none":
            flags.append(
                f"{field} ({column}): source states 'none' — "
                "value set to null, raw value kept"
            )
        return None, flags

    # ---- Text fields -------------------------------------------------------
    if parse_rule == "text":
        return stripped, flags

    # ---- Float fields ------------------------------------------------------
    if parse_rule == "float":
        try:
            numeric = float(stripped)
        except ValueError:
            flags.append(
                f"{field} ({column}): could not parse '{stripped}' as float — "
                "value set to null, raw value kept"
            )
            return None, flags

        # Mole-fraction sanity: value > 1 is suspicious
        if unit == "mole_fraction" and numeric > 1.0:
            flags.append(
                f"{field} ({column}): mole fraction value {numeric} is above 1 — "
                "may already be a percent; conversion skipped, value set to null"
            )
            return None, flags

        # Unit conversion (single call site)
        converted, unit_flag = convert(numeric, unit, field, column)
        if unit_flag:
            flags.append(unit_flag)
            return None, flags
        assert converted is not None  # unit was known

        # Post-conversion sanity checks
        if field == "oxygen_pct" and not (0.0 <= converted <= 100.0):
            flags.append(
                f"{field} ({column}): value {converted:.4g}% is outside [0, 100] — "
                "value kept"
            )

        if field == "pressure_kpa" and converted <= 0:
            flags.append(
                f"pressure_kpa ({column}): source reports {numeric} {unit}, "
                f"physically implausible for a test condition; "
                "treated as not reported (raw value kept)"
            )
            return None, flags

        if field == "flow_cm_s" and converted < 0:
            flags.append(
                f"{field} ({column}): negative value {converted:.4g} — value kept"
            )

        return converted, flags

    # ---- Unknown parse rule ------------------------------------------------
    flags.append(
        f"{field} ({column}): unknown parse rule '{parse_rule}' — "
        "value set to null"
    )
    return None, flags
