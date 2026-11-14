"""Where T5 reads its data. This is the one file to change when the record routes move to the database.

The pages take their record ids from the record routes, and those routes serve the sample data today.
T5 reads the same source, so it knows the same records.

The other T5 files call these functions through the module, as data.records(). They do not import
a function by its name, and they do not change the lists that come back: the lists are shared.
"""
from typing import Any, Dict, Iterable, List

from .. import fixtures

Record = Dict[str, Any]

SAMPLE = "This answer uses sample data, not verified PSI data."
PARSED = "This answer uses data that a program read from PSI tables. No person checked it."


def records() -> List[Record]:
    return fixtures.investigations()


def tests() -> List[Record]:
    return fixtures.tests()


def topics() -> List[str]:
    return fixtures.meta()["topics"]


def fuel_classes() -> List[str]:
    return fixtures.meta()["fuel_classes"]


def unchecked_notes(used: Iterable[Record]) -> List[str]:
    """The notes about data that no person checked, for the records and the test rows that an answer uses."""
    statuses = {item.get("data_status") for item in used}
    return [note for status, note in (("sample", SAMPLE), ("parsed", PARSED)) if status in statuses]
