"""Task T3. Tests routes — list with filters/pagination and detail."""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Response

from ..data_access import get_test, list_tests
from ..schemas import Paginated, TestRow

router = APIRouter(tags=["test rows"])


def _add_source_header(response: Response, source: str) -> None:
    response.headers["X-Data-Source"] = source


@router.get("/tests", response_model=Paginated[TestRow])
def list_tests_route(
    response: Response,
    investigation_id: Optional[str] = None,
    fuel: Optional[str] = None,
    outcome: Optional[str] = None,
    min_oxygen: Optional[float] = None,
    max_oxygen: Optional[float] = None,
    min_pressure_kpa: Optional[float] = None,
    max_pressure_kpa: Optional[float] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    rows, total, source = list_tests(
        investigation_id=investigation_id,
        fuel=fuel,
        outcome=outcome,
        min_oxygen=min_oxygen,
        max_oxygen=max_oxygen,
        min_pressure_kpa=min_pressure_kpa,
        max_pressure_kpa=max_pressure_kpa,
        page=page,
        page_size=page_size,
    )
    _add_source_header(response, source)
    return Paginated[TestRow](items=rows, page=page, page_size=page_size, total=total)


@router.get("/tests/{test_id:path}", response_model=TestRow)
def get_test_route(test_id: str, response: Response):
    row, source = get_test(test_id)
    _add_source_header(response, source)
    if row is None:
        raise HTTPException(status_code=404, detail=f'Test "{test_id}" was not found.')
    return row
