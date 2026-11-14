"""Step 2: fixed rules for a mapping file. No model is used here.

An error stops a proposal and an approval. A warning stops an approval until a
person changes the mapping or accepts the warning by name.
"""
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

from pydantic import ValidationError

from app.schemas import MappingFile

from .tables import Table

# How a unit can appear in a column name, in lower case. A unit inside a longer
# unit does not count: "m/s" must not match "cm/s".
UNIT_PATTERNS = {
    "percent": r"%|percent|(?<![a-z])pct(?![a-z])",
    "mole_fraction": r"mol(e|ar)?\s*frac",
    "kPa": r"(?<![a-z])kpa(?![a-z])",
    "mmHg": r"(?<![a-z])mm\s*hg(?![a-z])",
    "psi": r"(?<![a-z])psi[ag]?(?![a-z])",
    "atm": r"(?<![a-z])atm(?![a-z])",
    "cm/s": r"(?<![a-z])cm\s*/\s*s(ec)?(?![a-z])",
    "mm/s": r"(?<![a-z])mm\s*/\s*s(ec)?(?![a-z])",
    "m/s": r"(?<![a-z])m\s*/\s*s(ec)?(?![a-z])",
}


@dataclass
class CheckResult:
    errors: List[str] = field(default_factory=list)
    warnings: Dict[str, str] = field(default_factory=dict)  # key -> text; the key is what a person accepts


def shape_errors(error: ValidationError) -> List[str]:
    """The messages of a failed MappingFile, as plain sentences."""
    messages = []
    for item in error.errors():
        place = ".".join(str(part) for part in item["loc"])
        text = item["msg"].replace("Value error, ", "")
        messages.append(f"{place}: {text}" if place else text)
    return messages


def unit_is_visible(unit: str, column_name: str) -> bool:
    return re.search(UNIT_PATTERNS[unit], column_name.lower()) is not None


def _numbers(table: Table, column_name: str) -> List[float]:
    values = []
    for row in table.rows:
        try:
            values.append(float(row.get(column_name, "")))
        except ValueError:
            continue
    return values


def check_mapping(mapping: MappingFile, table: Table) -> CheckResult:
    result = CheckResult()
    listed = [column.source_column for column in mapping.columns]
    for name in table.header:
        if name not in listed:
            result.errors.append(f"The table column {name!r} is missing from the mapping.")
    for name in listed:
        if name not in table.header:
            result.errors.append(f"The mapping lists {name!r}, which is not a column of the table.")

    for column in mapping.columns:
        name = column.source_column
        if column.unit is None or name not in table.header:
            continue
        if not unit_is_visible(column.unit, name):
            result.warnings[f"unit_not_in_column_name:{name}"] = (
                f"{name!r} feeds {column.target_field} as {column.unit}, but the column name does not show that unit."
            )
        values = _numbers(table, name)
        if not values:
            continue
        if column.target_field == "oxygen_pct":
            if column.unit == "percent" and max(values) <= 1:
                result.warnings[f"percent_looks_like_fraction:{name}"] = (
                    f"{name!r} is declared as percent, but every value is 1 or less. It looks like a mole fraction."
                )
            if column.unit == "percent" and max(values) > 100:
                result.warnings[f"oxygen_above_100:{name}"] = f"{name!r} has an oxygen value above 100 percent."
            if column.unit == "mole_fraction" and max(values) > 1:
                result.warnings[f"fraction_above_1:{name}"] = f"{name!r} is declared as a mole fraction, but a value is above 1."
            if min(values) < 0:
                result.warnings[f"negative_value:{name}"] = f"{name!r} has a negative value."
        elif column.target_field == "pressure_kpa":
            if min(values) <= 0:
                result.warnings[f"pressure_not_positive:{name}"] = f"{name!r} has a pressure of zero or less."
        elif column.target_field == "flow_cm_s":
            if min(values) < 0:
                result.warnings[f"negative_value:{name}"] = f"{name!r} has a negative value."
    return result


def check_file(path, table: Table) -> CheckResult:
    """Check a mapping file on disk. A file that does not fit the shape gives errors, not an exception."""
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return CheckResult(errors=[f"The mapping file cannot be read: {error}"])
    try:
        mapping = MappingFile.model_validate(payload)
    except ValidationError as error:
        return CheckResult(errors=shape_errors(error))
    return check_mapping(mapping, table)
