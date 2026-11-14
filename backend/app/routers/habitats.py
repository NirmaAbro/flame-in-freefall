"""Task T3. Habitats route — list ordered by id."""
from typing import List

from fastapi import APIRouter, Response

from ..data_access import list_habitats
from ..schemas import Habitat

router = APIRouter(tags=["test rows"])


def _add_source_header(response: Response, source: str) -> None:
    response.headers["X-Data-Source"] = source


@router.get("/habitats", response_model=List[Habitat])
def list_habitats_route(response: Response):
    rows, source = list_habitats()
    _add_source_header(response, source)
    return rows
