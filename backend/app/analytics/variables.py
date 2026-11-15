"""GET /investigations/{id}/variables: which fields of its test rows a record varied and which it held constant.

Only the fields of the test-row contract are read. A raw column of the PSI table, such as the
fan setting of BASS-II, is not a contract field, so it is not in the answer.
"""
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from . import data

Record = Dict[str, Any]

FIELDS = ("fuel", "geometry", "oxygen_pct", "pressure_kpa", "flow_cm_s", "diluent", "outcome")
NUMBER_FIELDS = ("oxygen_pct", "pressure_kpa", "flow_cm_s")
MAX_VALUES = 12
DECIMALS = 6  # enough for every unit in use; it removes noise such as 14.000000000000002

NO_ROWS = "No test rows are indexed for this record."


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def number_text(value: float) -> str:
    """A plain decimal: "85" for 85.0 and "0.00005" for 5e-05."""
    if value == 0:
        return "0"
    text = format(Decimal(repr(float(value))), "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def summarise(rows: List[Record]) -> Tuple[List[Record], List[str]]:
    """One entry for each contract field of the given test rows, and the notes about those fields."""
    entries: List[Record] = []
    notes: List[str] = []
    for field in FIELDS:
        lowest = highest = None
        if field in NUMBER_FIELDS:
            reported = [round(float(row[field]), DECIMALS) for row in rows if is_number(row.get(field))]
            different = sorted(set(reported))
            values = [number_text(number) for number in different] if len(different) <= MAX_VALUES else []
            if different:
                lowest, highest = different[0], different[-1]
            too_many = "They are not listed."
        else:
            reported = [" ".join(row[field].split()) for row in rows if isinstance(row.get(field), str) and row[field].strip()]
            times: Dict[str, int] = {}
            spelling: Dict[str, str] = {}
            for text in reported:  # capital letters and spaces make no new value; the first spelling is shown
                key = text.casefold()
                times[key] = times.get(key, 0) + 1
                spelling.setdefault(key, text)
            different = list(times)  # in the order of first appearance
            shown = different if len(different) <= MAX_VALUES else sorted(different, key=lambda key: -times[key])[:MAX_VALUES]
            values = [spelling[key] for key in shown]
            too_many = f"The {MAX_VALUES} most frequent are shown."
        status = "not_reported" if not different else "constant" if len(different) == 1 else "varied"
        entries.append({"field": field, "status": status, "values": values, "minimum": lowest, "maximum": highest})
        missing = len(rows) - len(reported)
        if reported and missing:
            notes.append(f"{missing} of {len(rows)} tests {'does' if missing == 1 else 'do'} not report {field}.")
        if len(different) > MAX_VALUES:
            notes.append(f"{field} has {len(different)} different values. {too_many}")
    return entries, notes


def spans(rows: List[Record]) -> Dict[str, Tuple[float, float]]:
    """The lowest and the highest value of each number field that at least one of the rows reports."""
    entries, _ = summarise(rows)
    return {entry["field"]: (entry["minimum"], entry["maximum"]) for entry in entries if entry["minimum"] is not None}


def build(record_id: str) -> Optional[Record]:
    """The answer for one record. None when the record is not known."""
    record = data.resolve_record(record_id, data.records())
    if record is None:
        return None
    canonical_id = record["id"]
    rows = [row for row in data.tests() if row.get("investigation_id") == canonical_id]
    if not rows:
        return {"investigation_id": canonical_id, "test_count": 0, "variables": [], "notes": [NO_ROWS]}
    entries, notes = summarise(rows)
    return {"investigation_id": canonical_id, "test_count": len(rows), "variables": entries, "notes": notes + data.unchecked_notes(rows)}
