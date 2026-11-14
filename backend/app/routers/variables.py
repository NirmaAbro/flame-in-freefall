"""Task T5. GET /investigations/{id}/variables. The logic is in app/analytics/variables.py."""
from fastapi import APIRouter, HTTPException

from ..analytics import variables
from ..schemas import VariablesResponse

router = APIRouter(tags=["compare and coverage"])


@router.get("/investigations/{investigation_id}/variables", response_model=VariablesResponse)
def get_variables(investigation_id: str):
    answer = variables.build(investigation_id)
    if answer is None:
        raise HTTPException(
            status_code=404,
            detail=f'Investigation "{investigation_id}" was not found in the indexed records.',
        )
    return answer
