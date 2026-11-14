"""GET /analytics/coverage: the number of indexed records for each pair of topic and fuel class.

The rows and the columns are the fixed lists of the Explore filters, so each cell of the
Research Map can link to Explore. A record outside both lists is counted in a note, not hidden.
"""
from typing import Any, Dict, List

from . import data

Record = Dict[str, Any]

COUNT = "Each number is the count of indexed records with that topic and that fuel class."
MULTI = "A record with several topics or fuel classes counts in each cell that matches."
GAP = "A gap means that no indexed record matches. It does not mean that no research exists."


def build() -> Record:
    rows, columns = list(data.topics()), list(data.fuel_classes())  # copies: the lists are shared
    records = data.records()
    cells: List[Record] = []
    placed: Dict[str, Record] = {}
    for topic in rows:
        for fuel_class in columns:
            matching = [record for record in records if topic in (record.get("topic_tags") or []) and fuel_class in (record.get("fuel_classes") or [])]
            cells.append({"row": topic, "column": fuel_class, "count": len(matching), "investigation_ids": [record["id"] for record in matching]})
            placed.update((record["id"], record) for record in matching)

    notes = [COUNT, MULTI, GAP]
    unplaced = sum(1 for record in records if record["id"] not in placed)
    if unplaced == 1:
        notes.append("1 indexed record matches no listed topic or no listed fuel class. The map does not show it.")
    elif unplaced:
        notes.append(f"{unplaced} indexed records match no listed topic or no listed fuel class. The map does not show them.")
    return {
        "row_dimension": "Research topic",
        "column_dimension": "Fuel / material class",
        "rows": rows,
        "columns": columns,
        "cells": cells,
        "method_notes": notes + data.unchecked_notes(placed.values()),
    }
