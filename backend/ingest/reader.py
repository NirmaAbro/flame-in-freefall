"""CSV reader for PSI Experimental Tables (task T2).

Handles:
- utf-8-sig encoding (strips BOM automatically)
- Comma delimiter (all three files use comma)
- Header normalisation: collapse multiple spaces to one, strip leading/trailing
  whitespace, so "Calibrated  initial O2 % by vol " matches the mapping key
  "Calibrated initial O2 % by vol"
- Skips fully blank rows

Returns a list of dicts with normalised header keys and original string values.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Dict, List, Tuple


def _normalise_header(raw: str) -> str:
    """Collapse runs of whitespace to a single space and strip."""
    return re.sub(r"\s+", " ", raw).strip()


def read_csv(path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    """Read a PSI Experimental Table CSV.

    Returns:
        headers  – normalised column names (original order)
        rows     – list of {normalised_header: raw_cell_string} dicts,
                   blank rows excluded
    """
    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        # Normalise the fieldnames that DictReader parsed from the header row
        raw_fieldnames = reader.fieldnames or []
        norm_map = {raw: _normalise_header(raw) for raw in raw_fieldnames}
        headers = [norm_map[f] for f in raw_fieldnames]

        rows: List[Dict[str, str]] = []
        for raw_row in reader:
            # Rebuild with normalised keys
            row = {norm_map[k]: (v or "") for k, v in raw_row.items() if k in norm_map}
            # Skip fully blank rows (all values are empty strings)
            if not any(v.strip() for v in row.values()):
                continue
            rows.append(row)

    return headers, rows
