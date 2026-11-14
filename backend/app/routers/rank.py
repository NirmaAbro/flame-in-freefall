"""Task T4. Stub: the order of the investigations for one habitat."""
from fastapi import APIRouter, HTTPException

from .. import fixtures
from ..schemas import RankResponse

router = APIRouter(tags=["ranking"])


@router.get("/rank", response_model=RankResponse)
def rank(habitat: str):
    """Stub: title order and no scores. T4 writes the ranking and its formula."""
    found = next((h for h in fixtures.habitats() if h["id"] == habitat), None)
    if found is None:
        raise HTTPException(status_code=404, detail=f'Habitat "{habitat}" was not found.')
    records = sorted(fixtures.investigations(), key=lambda record: record["title"])
    return {
        "habitat": found,
        "items": [
            {
                "investigation_id": record["id"],
                "title": record["title"],
                "acronym": record["acronym"],
                "score": None,
                "parts": [],
            }
            for record in records
        ],
        "formula": None,
        "notes": ["Stub answer: the records are in title order, not ranked. Task T4 writes the ranking."],
    }
