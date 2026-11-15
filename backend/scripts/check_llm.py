"""Check the configured Google AI Studio model and endpoint."""
import logging
import sys

import httpx
from dotenv import load_dotenv

from app.config import get_settings
from app.llm import complete


logger = logging.getLogger(__name__)


def main() -> int:
    load_dotenv()
    settings = get_settings()
    if not settings.llm_api_key:
        print("None")
        return 1

    url = f"{settings.llm_base_url.rstrip('/')}/models"
    try:
        response = httpx.get(
            url,
            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            timeout=settings.llm_timeout,
        )
        response.raise_for_status()
        models = response.json().get("data", [])
        printed = 0
        for model in models:
            model_id = model.get("id", "")
            if "flash" in model_id.lower() or "pro" in model_id.lower():
                printed += 1
                if printed == 30:
                    break
        print(f"model ids count: {printed}")
    except (httpx.HTTPError, ValueError, TypeError, AttributeError) as error:
        logger.warning("Model listing failed: %s", str(error)[:200])
        print("None")
        return 1

    reply = complete(system="Reply with one word.", user="Say hello.")
    if reply is None:
        print("reply: None")
        return 1
    print(f"reply: {reply}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
