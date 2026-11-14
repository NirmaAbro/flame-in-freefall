"""Sample data for the stubs. Real data comes from the database after task T2."""
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _load(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def investigations() -> List[Dict[str, Any]]:
    """The frontend's 14 sample records (from src/lib/mock/data.ts)."""
    return _load("investigations.json")


@lru_cache(maxsize=None)
def meta() -> Dict[str, List[str]]:
    """Topics, fuel classes and featured ids (from src/lib/mock/data.ts)."""
    return _load("meta.json")


@lru_cache(maxsize=None)
def tests() -> List[Dict[str, Any]]:
    return _load("tests.json")


@lru_cache(maxsize=None)
def habitats() -> List[Dict[str, Any]]:
    return _load("habitats.json")
