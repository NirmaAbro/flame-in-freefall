"""Task T9. Stub: the habitat ranges, on sample data."""
from typing import List

from fastapi import APIRouter

from .. import fixtures
from ..schemas import Habitat

router = APIRouter(tags=["test rows"])


@router.get("/habitats", response_model=List[Habitat])
def list_habitats():
    return fixtures.habitats()
