"""Task T7. The two AI routes. The logic is in backend/ai/explain."""
from fastapi import APIRouter, Response

from ai.explain import ask, search

from ..schemas import AiAnswer, AiAskRequest, AiSearchIntent, AiSearchRequest
from .. import data_access

router = APIRouter(tags=["ai"])


@router.post("/ai/search", response_model=AiSearchIntent, response_model_exclude_none=True)
def ai_search(request: AiSearchRequest, response: Response):
    """Turn a question into filters of the record list. The model proposes, and the backend checks."""
    response.headers["X-Data-Source"] = (
        data_access.DATA_SOURCE_SUPABASE
        if data_access.has_credentials()
        else data_access.DATA_SOURCE_FIXTURE
    )
    return search.interpret(request.question)


@router.post("/ai/ask", response_model=AiAnswer)
def ai_ask(request: AiAskRequest, response: Response):
    """Answer from the selected records only, with a source mark for each statement."""
    response.headers["X-Data-Source"] = (
        data_access.DATA_SOURCE_SUPABASE
        if data_access.has_credentials()
        else data_access.DATA_SOURCE_FIXTURE
    )
    return ask.answer(request.question, request.investigation_ids)
