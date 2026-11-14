"""Unit conversion table for ingest (task T2).

One place only: add new units here, never in the per-field parser.

convert(value, unit, field) -> (converted_value_or_None, flag_or_None)
"""
from __future__ import annotations

from typing import Optional, Tuple

# ---------------------------------------------------------------------------
# Conversion factors to the canonical field unit
#   key  = unit string as it appears in the mapping file
#   value = multiplier to apply to the raw float
# ---------------------------------------------------------------------------
_FACTORS: dict[str, float] = {
    # oxygen_pct  (target: % by volume)
    "%": 1.0,
    "mole_fraction": 100.0,
    # pressure_kpa  (target: kPa)
    "mmHg": 0.133322368,
    "atm": 101.325,
    # flow_cm_s  (target: cm/s)
    "cm/s": 1.0,
}


def convert(
    value: float,
    unit: Optional[str],
    field: str,
    column: str,
) -> Tuple[Optional[float], Optional[str]]:
    """Return (converted_value, flag_string_or_None).

    Returns (None, flag) when the unit is unknown or missing.
    Never raises.
    """
    if unit is None:
        # Text fields — caller should not call convert at all, but be safe.
        return value, None

    factor = _FACTORS.get(unit)
    if factor is None:
        return None, (
            f"{field} ({column}): unknown unit '{unit}' — "
            "value set to null, raw value kept"
        )

    return value * factor, None
