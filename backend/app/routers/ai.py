"""Task T7. Stubs: the two AI routes answer without the model."""
from fastapi import APIRouter

from .. import fixtures
from ..schemas import AiAnswer, AiAskRequest, AiSearchIntent, AiSearchRequest

router = APIRouter(tags=["ai"])


@router.post("/ai/search", response_model=AiSearchIntent, response_model_exclude_none=True)
def ai_search(request: AiSearchRequest):
    """Stub: the question becomes a keyword search. T7 asks the model for filters."""
    return {
        "interpreted_as": {"q": request.question},
        "explanation": "Stub: the question is used as a keyword search. Task T7 connects the model.",
    }


@router.post("/ai/ask", response_model=AiAnswer)
def ai_ask(request: AiAskRequest):
    """Stub: a fixed text that cites the given sample records. T7 connects the model."""
    by_id = {record["id"]: record for record in fixtures.investigations()}
    cited = [by_id[i] for i in (request.investigation_ids or []) if i in by_id][:3]
    return {
        "answer": "Stub answer: the model is not connected yet. Task T7 writes this route.",
        "citations": [
            {"investigation_id": r["id"], "title": r["title"], "source_url": r["source_url"]} for r in cited
        ],
        "limitations": ["This is a stub answer on sample data, not an answer from the model."],
        "follow_up_questions": [],
    }
