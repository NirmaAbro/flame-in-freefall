"""One way to call the model that works with each form of app.llm.complete.

On 15 November 2026 that function changed its form three times:
    complete(system, user, timeout=None)        gives None when it has no answer
    complete(prompt, system="", timeout=30.0)   raises LLMUnavailable when the key is missing
A caller that names the inputs stops at each change. T6 and T7 call the model through this file.
It reads the names of the inputs first, and it gives None for "no answer" in both forms.
"""
import inspect
from typing import Callable, Optional


def call_model(complete: Callable[..., Optional[str]], system: str, user: str, timeout: Optional[float] = None) -> Optional[str]:
    """Send the two texts to `complete` in the form that it accepts. Return its reply, or None for no answer."""
    names = list(inspect.signature(complete).parameters)
    limit = {"timeout": timeout} if timeout is not None and "timeout" in names else {}
    try:
        if names and names[0] == "system":
            return complete(system, user, **limit)
        return complete(user, system=system, **limit)
    except Exception as error:
        if type(error).__name__ == "LLMUnavailable":  # the second form says "no key" in this way
            return None
        raise
