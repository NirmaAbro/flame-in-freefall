"""Step 3: a named person approves a mapping file.

Approval runs the check again. It is refused on any error, and on any warning
that the person did not accept by name.
"""
import json
from datetime import datetime, timezone

from pydantic import ValidationError

from app.schemas import MappingFile

from . import store
from .check import check_mapping, shape_errors
from .tables import TableError, read_table


class ApprovalRefused(Exception):
    """The file stays as it is. The message says what to do."""


def approve(source_id, data_dir, *, by, accept=(), table_path=None, now=None) -> MappingFile:
    name = (by or "").strip()
    if not name:
        raise ApprovalRefused("Approval needs the name of the person who approves (--by).")
    path = store.mapping_path(data_dir, source_id)
    if not path.is_file():
        raise ApprovalRefused(f"There is no mapping file for {source_id}.")
    try:
        table = read_table(table_path or store.find_table(data_dir, source_id))
    except TableError as error:
        raise ApprovalRefused(f"The check needs the table, and the table cannot be read. {error}") from error
    try:
        mapping = MappingFile.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except ValidationError as error:
        raise ApprovalRefused(f"{path.name} does not fit the mapping shape: " + " ".join(shape_errors(error))) from error
    except ValueError as error:
        raise ApprovalRefused(f"{path.name} is not valid JSON: {error}") from error
    if mapping.source_id != source_id:
        raise ApprovalRefused(f"{path.name} says it is the mapping of {mapping.source_id}, not of {source_id}.")
    if mapping.source_file != table.path.name:
        raise ApprovalRefused(
            f"{path.name} was made for the file {mapping.source_file!r}, but the table file is {table.path.name!r}."
        )

    result = check_mapping(mapping, table)
    if result.errors:
        raise ApprovalRefused("The check found errors. " + " ".join(result.errors))
    accepted = list(dict.fromkeys(accept))
    not_standing = [key for key in accepted if key not in result.warnings]
    if not_standing:
        raise ApprovalRefused("These warnings do not stand, so they cannot be accepted: " + ", ".join(not_standing))
    still_open = [key for key in result.warnings if key not in accepted]
    if still_open:
        raise ApprovalRefused(
            "These warnings stand. Change the mapping, or accept each one by name with --accept: " + ", ".join(still_open)
        )

    stamp = (now() if now else datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    approved = MappingFile.model_validate(
        {
            **mapping.model_dump(),
            "status": "approved",
            "approved_by": name,
            "approved_at": stamp,
            "accepted_warnings": sorted(accepted),
        }
    )
    store.write_json_atomic(path, approved.model_dump())
    return approved
