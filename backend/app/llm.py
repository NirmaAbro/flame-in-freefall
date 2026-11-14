"""The one place that calls the model. Tasks T6 and T7 use this function."""
import httpx

from .config import get_settings


class LLMUnavailable(RuntimeError):
    """The model is not configured or did not answer. The caller must fall back."""


def complete(prompt: str, system: str = "", timeout: float = 30.0) -> str:
    """Send one prompt to an OpenAI-compatible chat API and return the text."""
    settings = get_settings()
    if not settings.llm_api_key:
        raise LLMUnavailable("LLM_API_KEY is not set.")
    messages = [{"role": "system", "content": system}] if system else []
    messages.append({"role": "user", "content": prompt})
    try:
        response = httpx.post(
            f"{settings.llm_base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            json={"model": settings.llm_model, "messages": messages},
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as error:
        raise LLMUnavailable(str(error)) from error
