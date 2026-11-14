"""Task T3. Investigations routes — list with search/filter/pagination and detail."""
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Response

from ..data_access import (
    DATA_SOURCE_FIXTURE,
    get_investigation,
    list_investigations,
)
from ..schemas import Investigation, InvestigationListItem, Paginated

router = APIRouter(tags=["records"])


def _add_source_header(response: Response, source: str) -> None:
    response.headers["X-Data-Source"] = source


@router.get("/investigations", response_model=Paginated[InvestigationListItem])
def list_investigations_route(
    response: Response,
    q: Optional[str] = None,
    hardware_family: Optional[str] = None,
    # Legacy params kept for backward compatibility with existing tests/frontend
    topic: Optional[str] = None,
    platform: Optional[str] = None,
    material: Optional[str] = None,
    measurement: Optional[str] = None,
    sort: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    rows, total, source = list_investigations(
        q=q,
        hardware_family=hardware_family,
        page=page,
        page_size=page_size,
    )
    _add_source_header(response, source)
    items = [{**rec, "match_reasons": rec.get("match_reasons") or []} for rec in rows]
    return Paginated[InvestigationListItem](
        items=items,
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/investigations/{investigation_id}", response_model=Investigation)
def get_investigation_route(investigation_id: str, response: Response):
    rec, source = get_investigation(investigation_id)
    _add_source_header(response, source)
    if rec is None:
        raise HTTPException(
            status_code=404,
            detail=f'Investigation "{investigation_id}" was not found in the indexed records.',
        )
    return rec
