"""Where T5 reads its data: the shared data file of the record routes, app/data_access.py.

The pages take their record ids from the record routes. Those routes read through app/data_access.py:
the database when its two keys are set, the sample data when they are not. T5 reads through the same
file, so it always knows the same records. A database error becomes HTTP 503 there, and T5 lets it
pass: sample data is never shown in place of real data.

The two fixed lists (topics and fuel classes) come from the sample data, as in the filter route.

The other T5 files call these functions through the module, as data.records(). They do not import
a function by its name, and they do not change the lists that come back: the lists can be shared.
"""
from __future__ import annotations  # Python 3.9 cannot read "Record | None" without this line

from typing import Any, Dict, Iterable, List

from .. import data_access, fixtures

Record = Dict[str, Any]
PAGE = 1000  # the database gives at most 1,000 rows for one request

SAMPLE = "This answer uses sample data, not verified PSI data."
PARSED = "This answer uses data that a program read from PSI tables. No person checked it."
INVESTIGATION_ALIASES = {
    "psi-25": "psi-bass-ii",
    "psi-26": "psi-bass",
    "psi-68": "psi-flex-2",
    "psi-69": "psi-flex",
}


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


def source() -> str:
    """Return the source selected by the shared record routes."""
    return (
        data_access.DATA_SOURCE_SUPABASE
        if data_access.has_credentials()
        else data_access.DATA_SOURCE_FIXTURE
    )


def resolve_record(record_id: str, records: List[Record]) -> Record | None:
    """Find a record by canonical id, source id, acronym, or known fixture alias."""
    wanted = record_id.casefold()
    fixture_id = INVESTIGATION_ALIASES.get(wanted)
    return next(
        (
            record
            for record in records
            if str(record.get("id") or "").casefold()
            in {wanted, fixture_id}
            or str(record.get("source_id") or "").casefold() == wanted
            or str(record.get("acronym") or "").casefold() == wanted
        ),
        None,
    )


def unchecked_notes(used: Iterable[Record]) -> List[str]:
    """The notes about data that no person checked, for the records and the test rows that an answer uses."""
    statuses = {item.get("data_status") for item in used}
    return [note for status, note in (("sample", SAMPLE), ("parsed", PARSED)) if status in statuses]
