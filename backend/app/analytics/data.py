"""Where T5 reads its data: the shared data file of the record routes, app/data_access.py.

The pages take their record ids from the record routes. Those routes read through app/data_access.py:
the database when its two keys are set, the sample data when they are not. T5 reads through the same
file, so it always knows the same records. A database error becomes HTTP 503 there, and T5 lets it
pass: sample data is never shown in place of real data.

The two fixed lists (topics and fuel classes) come from the sample data, as in the filter route.

The other T5 files call these functions through the module, as data.records(). They do not import
a function by its name, and they do not change the lists that come back: the lists can be shared.
"""
from typing import Any, Dict, Iterable, List

from .. import data_access, fixtures

Record = Dict[str, Any]
PAGE = 1000  # the database gives at most 1,000 rows for one request

SAMPLE = "This answer uses sample data, not verified PSI data."
PARSED = "This answer uses data that a program read from PSI tables. No person checked it."


def records() -> List[Record]:
    """Every record that the record routes know."""
    found: List[Record] = []
    page = 1
    while True:
        rows, total, _source = data_access.list_investigations(page=page, page_size=PAGE)
        found.extend(rows)
        if not rows or len(found) >= total:
            return found
        page += 1


def tests() -> List[Record]:
    """Every test row that the test-row routes know."""
    rows, _source = data_access.iter_tests_csv()
    return list(rows)


def topics() -> List[str]:
    return fixtures.meta()["topics"]


def fuel_classes() -> List[str]:
    return fixtures.meta()["fuel_classes"]


def unchecked_notes(used: Iterable[Record]) -> List[str]:
    """The notes about data that no person checked, for the records and the test rows that an answer uses."""
    statuses = {item.get("data_status") for item in used}
    return [note for status, note in (("sample", SAMPLE), ("parsed", PARSED)) if status in statuses]
