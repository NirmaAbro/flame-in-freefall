"""Task T5. GET /investigations/{id}/variables. The logic is in app/analytics/variables.py."""
from fastapi import APIRouter, HTTPException, Response

from ..analytics import data, variables
from ..schemas import VariablesResponse

router = APIRouter(tags=["compare and coverage"])


@router.get("/investigations/{investigation_id}/variables", response_model=VariablesResponse)
def get_variables(investigation_id: str, response: Response):
    response.headers["X-Data-Source"] = data.source()
    answer = variables.build(investigation_id)
    if answer is None:
        raise HTTPException(
            status_code=404,
            detail=f'Investigation "{investigation_id}" was not found in the indexed records.',
        )
    return answer
