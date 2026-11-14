"""Task T5. GET /analytics/coverage. The logic is in app/analytics/coverage.py."""
from fastapi import APIRouter

from ..analytics import coverage
from ..schemas import CoverageResponse

router = APIRouter(tags=["compare and coverage"])


@router.get("/analytics/coverage", response_model=CoverageResponse)
def get_coverage():
    return coverage.build()
