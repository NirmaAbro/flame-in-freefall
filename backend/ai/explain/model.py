"""One call to the model. Nothing in its reply is trusted."""
import json
from typing import Any, Dict, Optional

from app import llm


def ask_model(user_text: str, system: str, timeout: float) -> Optional[Dict[str, Any]]:
    """Return the JSON object in the model's reply, or None for every kind of failure."""
    try:
        reply = llm.complete(prompt=user_text, system=system, timeout=timeout)
    except Exception:  # no failure of the model may break a route
        return None
    if not isinstance(reply, str):
        return None
    start, end = reply.find("{"), reply.rfind("}")  # the object can stand inside code marks or other text
    if start < 0 or end < start:
        return None
    try:
        value = json.loads(reply[start : end + 1])
    except ValueError:
        return None
    return value if isinstance(value, dict) else None
