"""POST /compare: the table of 1 to 4 records, the comparable numbers for the charts, and the notes.

The 10 rows and their names are those of the frontend's dummy backend (src/lib/mock/mockApi.ts).
A number is comparable when two or more different records report it with the same name and the
same unit. No unit is converted.
"""
from typing import Any, Dict, List, Optional, Tuple

from . import data, variables

Record = Dict[str, Any]

MAX_RECORDS = 4
PLAIN_ROWS = (("Research area", "research_area"), ("Platform", "platform"), ("Gravity environment", "environment"), ("Hardware", "hardware"))
LIST_ROWS = (("Fuel class", "fuel_classes"), ("Fuels / materials", "fuel_materials"), ("Topics", "topic_tags"), ("Measurement types", "measurement_types"))
ROW_FIELDS = (("oxygen_pct", "Oxygen", "% by volume"), ("pressure_kpa", "Pressure", "kPa"), ("flow_cm_s", "Flow", "cm/s"))

STORED = "Values are shown exactly as stored. Missing values are 'not reported', never zero."
CHARTS = "Numeric charts appear only when two or more records report the same parameter in the same unit."
ROW_CHARTS = "A chart of test rows shows the lowest and the highest value in the indexed test rows of each record."
FIRST_FOUR = "Only the first 4 selected records were used."
TOO_FEW = "A comparison needs at least 2 records."


def build(ids: List[str]) -> Record:
    wanted = list(dict.fromkeys(ids))  # each id once, at its first place
    by_id = {record["id"]: record for record in data.records()}
    known = [by_id[record_id] for record_id in wanted if record_id in by_id]
    records = known[:MAX_RECORDS]
    rows_of = {record["id"]: [row for row in data.tests() if row.get("investigation_id") == record["id"]] for record in records}
    from_rows = _row_parameters(records, rows_of)

    notes = [STORED, CHARTS] if records else []
    if from_rows:
        notes.append(ROW_CHARTS)
    missing = len(wanted) - len(known)
    if missing:
        notes.append(f"{missing} selected record{' was' if missing == 1 else 's were'} not found.")
    if len(known) > MAX_RECORDS:
        notes.append(FIRST_FOUR)
    if len(records) < 2:
        notes.append(TOO_FEW)
    used_rows = [row for rows in rows_of.values() for row in rows]
    return {
        "investigations": [
            {"id": record["id"], "title": record.get("title") or str(record["id"]), "acronym": _text(record.get("acronym")), "source_url": record.get("source_url") or ""}
            for record in records
        ],
        "rows": _rows(records) if records else [],
        "comparable_parameters": _stored_parameters(records) + from_rows,
        "notes": notes + data.unchecked_notes([*records, *used_rows]),
    }


# ---------- The table ----------


def _text(value: Any) -> Optional[str]:
    """A stored text as it is. None when it is missing or blank: a missing value never becomes an empty text."""
    if value is None or not str(value).strip():
        return None
    return str(value)


def _joined(values: Any) -> Optional[str]:
    return ", ".join(str(value) for value in values) if values else None


def _condition(condition: Record) -> str:
    value, unit = condition.get("value"), _text(condition.get("unit"))
    shown = variables.number_text(value) if variables.is_number(value) else str(value)
    return f"{condition.get('name')}: {shown}" + (f" {unit}" if unit else "")


def _rows(records: List[Record]) -> List[Record]:
    def row(name, read):
        return {"field": name, "cells": {record["id"]: {"value": read(record)} for record in records}}

    plain = [row(name, lambda record, key=key: _text(record.get(key))) for name, key in PLAIN_ROWS]
    lists = [row(name, lambda record, key=key: _joined(record.get(key))) for name, key in LIST_ROWS]
    conditions = row("Reported conditions", lambda record: _joined([_condition(c) for c in record.get("conditions") or []]))
    files = row("Linked files", lambda record: str(len(record["files"])) if record.get("files") else None)
    return [*plain, *lists, conditions, files]


# ---------- The comparable numbers ----------


def _label(record: Record) -> str:
    return _text(record.get("acronym")) or _text(record.get("title")) or str(record["id"])


def _parameter(name: str, unit: str, values: List[Tuple[Record, float]]) -> Record:
    """One chart. A record that has several values here gets numbered labels, such as "FLEX (1)"."""
    total: Dict[str, int] = {}
    for record, _ in values:
        total[record["id"]] = total.get(record["id"], 0) + 1
    seen: Dict[str, int] = {}
    bars = []
    for record, value in values:
        label = _label(record)
        if total[record["id"]] > 1:
            seen[record["id"]] = seen.get(record["id"], 0) + 1
            label = f"{label} ({seen[record['id']]})"
        bars.append({"investigation_id": record["id"], "label": label, "value": value})
    return {"name": name, "unit": unit, "values": bars}


def _stored_parameters(records: List[Record]) -> List[Record]:
    """From the stored conditions, in the order of their first appearance."""
    found: Dict[Tuple[str, str], List[Tuple[Record, float]]] = {}
    for record in records:
        for condition in record.get("conditions") or []:
            name, value, unit = condition.get("name"), condition.get("value"), condition.get("unit")
            if isinstance(name, str) and variables.is_number(value) and isinstance(unit, str) and unit.strip():
                found.setdefault((name, unit), []).append((record, float(value)))
    return [
        _parameter(name, unit, values)
        for (name, unit), values in found.items()
        if len({record["id"] for record, _ in values}) >= 2  # two values of one record are no comparison
    ]


def _row_parameters(records: List[Record], rows_of: Dict[str, List[Record]]) -> List[Record]:
    """From the test rows: the lowest and the highest value of oxygen, pressure and flow in each record."""
    spans = {record["id"]: variables.spans(rows_of[record["id"]]) for record in records}
    parameters = []
    for field, name, unit in ROW_FIELDS:
        having = [(record, spans[record["id"]][field]) for record in records if field in spans[record["id"]]]
        if len(having) < 2:
            continue
        if all(lowest == highest for _, (lowest, highest) in having):  # two equal charts would say the same
            parameters.append(_parameter(f"{name} in the test rows", unit, [(record, lowest) for record, (lowest, _) in having]))
        else:
            parameters.append(_parameter(f"{name}, lowest value in the test rows", unit, [(record, lowest) for record, (lowest, _) in having]))
            parameters.append(_parameter(f"{name}, highest value in the test rows", unit, [(record, highest) for record, (_, highest) in having]))
    return parameters
