"""The one place that calls the model. Tasks T6 and T7 use this function."""
from __future__ import annotations  # Python 3.9 cannot read "float | None" without this line

import logging
import time

import httpx

from .config import get_settings


logger = logging.getLogger(__name__)
_RETRYABLE_STATUSES = {429, 500, 502, 503}


class LLMUnavailable(RuntimeError):
    """Compatibility exception for callers that import the old exception."""


def _short_error(response: httpx.Response) -> str:
    body = response.text.replace("\n", " ").strip()
    return body[:200] or response.reason_phrase or "request failed"


def complete(system: str, user: str, timeout: float | None = None) -> str | None:
    """Send one prompt to an OpenAI-compatible chat API and return the text."""
    settings = get_settings()
    if not settings.llm_api_key:
        return None

    payload = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": settings.llm_max_tokens,
    }
    if settings.llm_reasoning_effort:
        payload["reasoning_effort"] = settings.llm_reasoning_effort

    request_timeout = settings.llm_timeout if timeout is None else timeout
    url = f"{settings.llm_base_url.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {settings.llm_api_key}"}

    for attempt in range(2):
        try:
            response = httpx.post(
                url,
                headers=headers,
                json=payload,
                timeout=request_timeout,
            )
            if response.status_code >= 400:
                error = _short_error(response).replace(settings.llm_api_key, "[redacted]")
                if response.status_code in _RETRYABLE_STATUSES and attempt == 0:
                    logger.warning("LLM request failed (status=%s): %s", response.status_code, error)
                    time.sleep(2)
                    continue
                logger.warning("LLM request failed (status=%s): %s", response.status_code, error)
                return None
            content = response.json()["choices"][0]["message"]["content"]
            return content if content else None
        except httpx.TimeoutException as error:
            logger.warning("LLM request failed (status=timeout): %s", str(error)[:200])
            if attempt == 0:
                time.sleep(2)
                continue
            return None
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as error:
            logger.warning("LLM request failed (status=unknown): %s", str(error)[:200])
            return None

    return None
