"""Task T5. GET /analytics/coverage. The logic is in app/analytics/coverage.py."""
from fastapi import APIRouter, Response

from ..analytics import coverage, data
from ..schemas import CoverageResponse

router = APIRouter(tags=["compare and coverage"])


@router.get("/analytics/coverage", response_model=CoverageResponse)
def get_coverage(response: Response):
    response.headers["X-Data-Source"] = data.source()
    return coverage.build()
