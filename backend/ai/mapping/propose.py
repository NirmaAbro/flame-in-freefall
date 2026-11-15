"""Step 1: ask the model for a mapping, and keep only what the contract allows.

The model's answer is untrusted. The tool takes the list of columns from it and
nothing else: the ids, the file name, the status and the approval fields are set here.
"""
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple

from pydantic import ValidationError

from app import llm
from app.config import get_settings
from app.schemas import MAPPING_UNITS, MappingFile

from . import store
from .check import CheckResult, check_mapping, shape_errors
from .tables import Table, read_table

SAMPLE_ROWS = 8
COLUMN_KEYS = ("source_column", "target_field", "unit", "confidence", "note")
RETRY_NOTE = "Your previous answer was not valid"
NO_REPLY = (
    "The model did not answer, so nothing was written. Check LLM_API_KEY, LLM_BASE_URL and LLM_MODEL. "
    "When a request failed, a line above this one gives the reason."
)

FIELD_MEANINGS = {
    "test_label": "the name or number that identifies one run",
    "fuel": "the fuel or the sample material",
    "geometry": "the shape and size of the sample or burner",
    "diluent": "the gas that dilutes the atmosphere",
    "outcome": "how the run ended",
    "oxygen_pct": "the oxygen level at the start of the run",
    "pressure_kpa": "the pressure of the atmosphere around the run",
    "flow_cm_s": "the speed of the air or gas flow",
}


class ProposeFailed(Exception):
    """No proposal was written. The message says why."""


class MappingExists(ProposeFailed):
    """A mapping file is already there, and --force was not given."""


@dataclass
class ProposeResult:
    path: Path
    copy_path: Path
    mapping: MappingFile
    check: CheckResult


def system_prompt() -> str:
    lines = [
        "You map the columns of one experiment table to a fixed list of fields.",
        "Rules:",
        "- Use only the fields and units listed below.",
        "- A field takes at most one column. Use null for every other column.",
        "- For a number field, give the unit that the column name states. If the column name states no unit"
        " from the list, use null for the field and for the unit.",
        "- Do not guess. When in doubt, use null and say why in the note.",
        "- List every column of the table exactly once, in the order of the table.",
        "Fields:",
    ]
    for name, meaning in FIELD_MEANINGS.items():
        units = MAPPING_UNITS.get(name)
        unit_text = f"a number; unit is one of: {', '.join(units)}" if units else "text; unit is null"
        lines.append(f"- {name}: {meaning} ({unit_text})")
    lines.append(
        'Answer with JSON only, in this form: {"columns": [{"source_column": "...", "target_field": "a field or null",'
        ' "unit": "a unit or null", "confidence": "high, medium or low", "note": "a short reason or null"}]}'
    )
    return "\n".join(lines)


def build_prompt(table: Table) -> Tuple[str, str]:
    """The instructions and the question. The question holds the header and the first rows, nothing else."""
    sample = [[row.get(name, "") for name in table.header] for row in table.rows[:SAMPLE_ROWS]]
    question = "The table's columns and its first rows, as JSON:\n" + json.dumps(
        {"columns": table.header, "first_rows": sample}, ensure_ascii=False, indent=1
    )
    return system_prompt(), question


def extract_json(text: str) -> dict:
    """Find the JSON object in an answer that may have text or code marks around it."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("The answer holds no JSON object.")
    try:
        value = json.loads(text[start : end + 1])
    except ValueError as error:
        raise ValueError(f"The answer is not valid JSON: {error}") from None
    if not isinstance(value, dict):
        raise ValueError("The answer is not a JSON object.")
    return value


def _clean(value):
    """Models often write the text 'null' where they mean no value."""
    if isinstance(value, str) and value.strip().lower() in ("", "null", "none"):
        return None
    return value


def build_mapping(answer: dict, table: Table, source_id: str, model_name: str) -> MappingFile:
    columns = answer.get("columns")
    if not isinstance(columns, list):
        raise ValueError('The answer has no "columns" list.')
    kept = []
    for entry in columns:
        if not isinstance(entry, dict):
            raise ValueError('Each entry of "columns" must be an object.')
        column = {key: _clean(entry.get(key)) for key in COLUMN_KEYS}
        if isinstance(column["confidence"], str):
            column["confidence"] = column["confidence"].strip().lower()
        if column["confidence"] not in ("high", "medium", "low"):
            column["confidence"] = None
        kept.append(column)
    try:
        return MappingFile(
            source_id=source_id,
            source_file=table.path.name,
            status="proposed",
            proposed_by=model_name,
            columns=kept,
        )
    except ValidationError as error:
        raise ValueError(" ".join(shape_errors(error))) from None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def propose(source_id, table_path, data_dir, *, complete=None, model_name=None, force=False, now=None) -> ProposeResult:
    """Write a proposed mapping file and an untouched copy, or raise ProposeFailed and write nothing."""
    target = store.mapping_path(data_dir, source_id)
    if target.exists() and not force:
        raise MappingExists(
            f"{target.name} already exists, and a new proposal would replace it. Use --force to replace it."
        )
    table = read_table(table_path)
    complete = complete or llm.complete
    model_name = model_name or get_settings().llm_model
    system, question = build_prompt(table)

    mapping, check, problem = None, None, ""
    for attempt in range(2):
        ask = question if attempt == 0 else f"{question}\n\n{RETRY_NOTE}: {problem}\nReturn the full JSON again."
        try:
            text = complete(prompt=ask, system=system)
        except llm.LLMUnavailable as error:  # app.llm.complete raises this for a missing key
            raise ProposeFailed(f"The model did not answer, so nothing was written. Reason: {error}") from error
        if text is None:  # and it gives None for a failed request
            raise ProposeFailed(NO_REPLY)
        try:
            candidate = build_mapping(extract_json(text), table, source_id, model_name)
        except ValueError as error:
            problem = str(error)
            continue
        check = check_mapping(candidate, table)
        if check.errors:
            problem = " ".join(check.errors)
            continue
        mapping = candidate
        break
    if mapping is None:
        raise ProposeFailed(f"The model gave an invalid answer twice, so nothing was written. Last problem: {problem}")

    payload = mapping.model_dump()
    stamp = (now or _utc_now)().strftime("%Y%m%dT%H%M%SZ")
    copy_path = store.new_proposal_path(data_dir, source_id, stamp)
    store.write_json_atomic(copy_path, payload)  # the untouched copy first: the score reads it
    store.write_json_atomic(target, payload)
    return ProposeResult(path=target, copy_path=copy_path, mapping=mapping, check=check)
