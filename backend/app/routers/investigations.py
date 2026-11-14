"""Task T3. Stub: the record list and the detail record, on sample data."""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from .. import fixtures
from ..schemas import Investigation, InvestigationListItem, Paginated

router = APIRouter(tags=["records"])


@router.get("/investigations", response_model=Paginated[InvestigationListItem])
def list_investigations(
    q: Optional[str] = None,
    topic: Optional[str] = None,
    platform: Optional[str] = None,
    material: Optional[str] = None,
    measurement: Optional[str] = None,
    sort: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(6, ge=1, le=100),
):
    """Stub: every sample record, in pages. T3 adds search, filters, sorting and match reasons."""
    records = fixtures.investigations()
    start = (page - 1) * page_size
    items = [{**record, "match_reasons": []} for record in records[start : start + page_size]]
    return {"items": items, "page": page, "page_size": page_size, "total": len(records)}


@router.get("/investigations/{investigation_id}", response_model=Investigation)
def get_investigation(investigation_id: str):
    for record in fixtures.investigations():
        if record["id"] == investigation_id:
            return record
    raise HTTPException(
        status_code=404,
        detail=f'Investigation "{investigation_id}" was not found in the indexed records.',
    )
