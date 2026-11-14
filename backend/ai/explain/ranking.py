"""The link from the ask route to the habitat ranking of task T4.

T7 does not rank. When a question names a habitat, this module asks the T4 code
for the ranking of that habitat and returns the best investigations with their
scores. It changes nothing in T4. Every failure means "no ranking", and the ask
route then works as it does without this link.
"""
import re
from typing import Any, Dict, List, NamedTuple, Optional

from . import records

Record = Dict[str, Any]
SHORT = 6  # a shorter id or name of a habitat, such as "iss", must stand as a whole word


class Ranked(NamedTuple):
    habitat: Record
    items: List[Record]  # the best investigations, each with a "ranking" entry; empty when no test matches


def _squash(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _position(phrase: str, lower: str, squashed: str) -> int:
    """Where the question names the phrase, counted in letters and digits. -1 when it does not."""
    key = _squash(phrase)
    if not key:
        return -1
    if len(key) >= SHORT:
        return squashed.find(key)
    match = re.search(r"(?<![a-z0-9])" + re.escape(key) + r"(?![a-z0-9])", lower)
    return len(_squash(lower[: match.start()])) if match else -1


def find_habitat(question: str, habitats: List[Record]) -> Optional[Record]:
    """The habitat that the question names by its id or its name, with or without spaces and hyphens.

    The text in brackets at the end of a name, such as "(4.3 psia, pure O2)", is not part of the name.
    The habitat that is named first wins.
    """
    lower = question.lower()
    squashed = _squash(question)
    found = []
    for habitat in habitats:
        phrases = (str(habitat.get("id") or ""), str(habitat.get("name") or "").split("(")[0])
        positions = [position for position in (_position(phrase, lower, squashed) for phrase in phrases) if position >= 0]
        if positions:
            found.append((min(positions), str(habitat["id"]), habitat))
    return min(found, key=lambda item: item[:2])[2] if found else None


def for_question(question: str) -> Optional[Ranked]:
    """The ranking for the habitat that the question names. None when it names no habitat or the ranking fails."""
    try:
        from app.ranking.score import rank_investigations  # the T4 code, used as it is
        from app.routers import rank as rank_route

        habitats, investigations, tests_by_investigation, _source = rank_route._load_data()
        habitat = find_habitat(question, habitats)
        if habitat is None:
            return None
        scores = rank_investigations(habitat=habitat, investigations=investigations, tests_by_investigation=tests_by_investigation)
        full_records = {record["id"]: record for record in records.load_records()}
        ranked_records = {record["id"]: record for record in investigations}
        items: List[Record] = []
        for score in scores:  # T4 returns the best first
            if not score.score or score.score <= 0:
                continue
            record = dict(full_records.get(score.investigation_id) or ranked_records[score.investigation_id])
            record["ranking"] = {
                "score": round(score.score, 2),
                "tests_total": score.tests_total,
                "tests_full": score.tests_full,
                "tests_partial": score.tests_partial,
                "tests_none": score.tests_none,
            }
            items.append(record)
            if len(items) == records.MAX_RECORDS:
                break
        return Ranked(dict(habitat), items)
    except Exception:  # the link must never break the ask route
        return None
