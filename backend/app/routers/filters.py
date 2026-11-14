"""Task T3. Stub: the filter values of the Explore page, from sample data."""
from fastapi import APIRouter

from .. import fixtures
from ..schemas import FilterOptions

router = APIRouter(tags=["records"])


@router.get("/filters", response_model=FilterOptions)
def get_filters():
    records = fixtures.investigations()
    return {
        "topics": fixtures.meta()["topics"],
        "platforms": sorted({record["platform"] for record in records if record["platform"]}),
        "materials": fixtures.meta()["fuel_classes"],
        "measurements": sorted({m for record in records for m in record["measurement_types"]}),
    }
