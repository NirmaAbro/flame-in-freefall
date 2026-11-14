"""Task T5. Stub: a short compare answer for the requested sample records."""
from fastapi import APIRouter

from .. import fixtures
from ..schemas import CompareRequest, CompareResponse

router = APIRouter(tags=["compare and coverage"])


@router.post("/compare", response_model=CompareResponse)
def compare(request: CompareRequest):
    """Stub: four plain rows. T5 adds the other rows and the comparable parameters."""
    by_id = {record["id"]: record for record in fixtures.investigations()}
    records = [by_id[i] for i in request.investigation_ids if i in by_id]

    def row(field: str, key: str):
        return {"field": field, "cells": {r["id"]: {"value": r[key]} for r in records}}

    return {
        "investigations": [
            {"id": r["id"], "title": r["title"], "acronym": r["acronym"], "source_url": r["source_url"]}
            for r in records
        ],
        "rows": [
            row("Research area", "research_area"),
            row("Platform", "platform"),
            row("Gravity environment", "environment"),
            row("Hardware", "hardware"),
        ],
        "comparable_parameters": [],
        "notes": ["Stub answer on sample data. Task T5 writes the full comparison."],
    }
