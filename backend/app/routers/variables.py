"""Task T5. Stub: which fields an investigation varied and which it held constant."""
from fastapi import APIRouter, HTTPException

from .. import fixtures
from ..schemas import VariablesResponse

router = APIRouter(tags=["compare and coverage"])


@router.get("/investigations/{investigation_id}/variables", response_model=VariablesResponse)
def get_variables(investigation_id: str):
    """Stub: the test count only. T5 computes the varied and the constant fields."""
    if not any(record["id"] == investigation_id for record in fixtures.investigations()):
        raise HTTPException(
            status_code=404,
            detail=f'Investigation "{investigation_id}" was not found in the indexed records.',
        )
    test_count = sum(row["investigation_id"] == investigation_id for row in fixtures.tests())
    return {
        "investigation_id": investigation_id,
        "test_count": test_count,
        "variables": [],
        "notes": ["Stub answer on sample data. Task T5 computes the varied and the constant fields."],
    }
