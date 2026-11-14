"""Task T5. Stub: the coverage matrix (topic by fuel class), counted from sample data."""
from fastapi import APIRouter

from .. import fixtures
from ..schemas import CoverageResponse

router = APIRouter(tags=["compare and coverage"])


@router.get("/analytics/coverage", response_model=CoverageResponse)
def get_coverage():
    records = fixtures.investigations()
    topics = fixtures.meta()["topics"]
    fuel_classes = fixtures.meta()["fuel_classes"]
    cells = []
    for topic in topics:
        for fuel_class in fuel_classes:
            ids = [
                record["id"]
                for record in records
                if topic in record["topic_tags"] and fuel_class in record["fuel_classes"]
            ]
            cells.append({"row": topic, "column": fuel_class, "count": len(ids), "investigation_ids": ids})
    return {
        "row_dimension": "Research topic",
        "column_dimension": "Fuel / material class",
        "rows": topics,
        "columns": fuel_classes,
        "cells": cells,
        "method_notes": [
            "Counts come from the sample data served by the backend stubs.",
            "A gap means 'no matching indexed record'. It does not mean that no research exists.",
        ],
    }
