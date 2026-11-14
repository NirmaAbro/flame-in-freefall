"""Task T7. The two AI routes. The logic is in backend/ai/explain."""
from fastapi import APIRouter

from ai.explain import ask, search

from ..schemas import AiAnswer, AiAskRequest, AiSearchIntent, AiSearchRequest

router = APIRouter(tags=["ai"])


@router.post("/ai/search", response_model=AiSearchIntent, response_model_exclude_none=True)
def ai_search(request: AiSearchRequest):
    """Turn a question into filters of the record list. The model proposes, and the backend checks."""
    return search.interpret(request.question)


@router.post("/ai/ask", response_model=AiAnswer)
def ai_ask(request: AiAskRequest):
    """Answer from the selected records only, with a source mark for each statement."""
    return ask.answer(request.question, request.investigation_ids)
