"""The records that the AI routes may use.

They must be the same records as the record routes serve (GET /investigations),
or a source can lead to a page that does not exist. Today those routes serve the
sample records. When they move to the database, load_records() moves with them.
"""
import re
from typing import Any, Dict, List

from app import fixtures

Record = Dict[str, Any]

MAX_RECORDS = 4  # the Compare page also sends at most 4
PSI_HOME = "https://psi.nasa.gov/physci/repo"  # the link for a record that has none
STOP_WORDS = frozenset(
    "what which with have about same does this that from were been when where they their there these those "
    "into than them your find show tell give list related known available evidence deal".split()
)
ACRONYM_POINTS = 5


def load_records() -> List[Record]:
    return fixtures.investigations()


def _text(record: Record) -> str:
    parts = [record.get("title"), record.get("acronym"), record.get("summary")]
    for key in ("topic_tags", "fuel_materials", "measurement_types"):
        parts.extend(record.get(key) or [])
    return " ".join(part for part in parts if part).lower()


def search(question: str, records: List[Record]) -> List[Record]:
    """The best records for a question, by a fixed keyword rule. The same question always gives the same list."""
    words = {word for word in re.findall(r"[a-z0-9]+", question.lower()) if len(word) > 3 and word not in STOP_WORDS}
    scored = []
    for record in records:
        text = _text(record)
        points = sum(1 for word in words if word in text)
        acronym = record.get("acronym")
        # The acronym counts only as it is written, and "BASS-II" must not count for BASS.
        if acronym and re.search(r"(?<![A-Za-z0-9-])" + re.escape(acronym) + r"(?![A-Za-z0-9-])", question):
            points += ACRONYM_POINTS
        if points:
            scored.append((-points, str(record["id"]), record))
    scored.sort(key=lambda item: item[:2])
    return [record for _, _, record in scored[:MAX_RECORDS]]


def allowed_values(records: List[Record]) -> Dict[str, List[str]]:
    """The values that a filter may have. They are the values of GET /filters."""
    return {
        "topic": list(fixtures.meta()["topics"]),
        "material": list(fixtures.meta()["fuel_classes"]),
        "platform": sorted({record["platform"] for record in records if record.get("platform")}),
        "measurement": sorted({value for record in records for value in (record.get("measurement_types") or [])}),
    }


def matches(record: Record, filters: Dict[str, str]) -> bool:
    """True when the record passes every filter, by the rules of the record list."""
    return (
        ("topic" not in filters or filters["topic"] in (record.get("topic_tags") or []))
        and ("platform" not in filters or record.get("platform") == filters["platform"])
        and ("material" not in filters or filters["material"] in (record.get("fuel_classes") or []))
        and ("measurement" not in filters or filters["measurement"] in (record.get("measurement_types") or []))
    )
