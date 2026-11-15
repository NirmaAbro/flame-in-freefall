"""Task T5. POST /compare. The logic is in app/analytics/comparison.py."""
from fastapi import APIRouter, Response

from ..analytics import comparison
from ..schemas import CompareRequest, CompareResponse

router = APIRouter(tags=["compare and coverage"])


@router.post("/compare", response_model=CompareResponse)
def compare(request: CompareRequest, response: Response):
    """A problem with the selected records goes into the notes, so a well-formed request always gets HTTP 200."""
    response.headers["X-Data-Source"] = comparison.data_source()
    return comparison.build(request.investigation_ids)
