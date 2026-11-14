"""Task T9. Stub: the test rows (one row per test of an investigation), on sample data."""
from typing import List, Optional

from fastapi import APIRouter, HTTPException

from .. import fixtures
from ..schemas import TestRow

router = APIRouter(tags=["test rows"])


@router.get("/tests", response_model=List[TestRow])
def list_tests(investigation_id: Optional[str] = None):
    """Stub: the sample rows, for one investigation or for all. T9 adds the other filters."""
    rows = fixtures.tests()
    if investigation_id:
        rows = [row for row in rows if row["investigation_id"] == investigation_id]
    return rows


@router.get("/tests/{test_id}", response_model=TestRow)
def get_test(test_id: str):
    for row in fixtures.tests():
        if row["id"] == test_id:
            return row
    raise HTTPException(status_code=404, detail=f'Test "{test_id}" was not found.')
