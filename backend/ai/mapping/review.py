"""What a person reads before approving: each column, sample values, and the check results."""
from app.schemas import MappingFile

from .check import CheckResult
from .tables import Table

SAMPLES = 3


def _samples(table: Table, column_name: str):
    seen = []
    for row in table.rows:
        value = row.get(column_name, "")
        if value and value not in seen:
            seen.append(value)
        if len(seen) == SAMPLES:
            break
    return seen


def render_review(mapping: MappingFile, table: Table, check: CheckResult) -> str:
    lines = [
        f"Mapping of {mapping.source_id} ({mapping.source_file})",
        f"Status: {mapping.status}. Proposed by: {mapping.proposed_by}."
        + (f" Approved by: {mapping.approved_by} at {mapping.approved_at}." if mapping.approved_by else ""),
        "",
        "Column  ->  field [unit]  |  sample values  |  confidence, note",
    ]
    width = max(len(column.source_column) for column in mapping.columns)
    for column in mapping.columns:
        target = column.target_field or "(not used)"
        unit = f" [{column.unit}]" if column.unit else ""
        samples = ", ".join(_samples(table, column.source_column)) or "(no values)"
        extra = ", ".join(part for part in (column.confidence, column.note) if part)
        lines.append(f"{column.source_column.ljust(width)}  ->  {target}{unit}  |  {samples}" + (f"  |  {extra}" if extra else ""))

    lines.append("")
    lines.append("Errors:" if check.errors else "Errors: none")
    lines.extend(f"  - {error}" for error in check.errors)
    lines.append("Warnings (each must be settled before approval):" if check.warnings else "Warnings: none")
    lines.extend(f"  - {key}  ({text})" for key, text in check.warnings.items())
    if mapping.accepted_warnings:
        lines.append("Accepted warnings: " + ", ".join(mapping.accepted_warnings))
    return "\n".join(lines)
