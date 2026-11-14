"""Step 4: how good are the model's proposals?

The score compares the untouched copy of each proposal with a gold mapping that
a person wrote by hand. It never reads the corrected file in data/mappings/.

Most columns of a table are unused, so "all columns correct" flatters a model
that maps nothing. The main number is "mapped columns found".
"""
from dataclasses import dataclass, field
from typing import List

from pydantic import ValidationError

from . import store


@dataclass
class TableScore:
    source_id: str
    mapped_found: int = 0  # columns the gold uses, mapped to the same field and unit
    mapped_total: int = 0  # columns the gold uses
    all_correct: int = 0  # every column, used or unused
    all_total: int = 0
    wrong_field: int = 0
    wrong_unit: int = 0
    missed: int = 0  # the gold uses the column, the proposal does not
    false_mappings: List[str] = field(default_factory=list)  # the proposal uses a column the gold leaves unused


@dataclass
class ScoreReport:
    tables: List[TableScore] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def render(self) -> str:
        lines = ["Score of the model's untouched proposals against the gold mappings"]
        for table in self.tables:
            lines.append(
                f"{table.source_id}: mapped columns found {table.mapped_found} of {table.mapped_total}"
                f" | all columns correct {table.all_correct} of {table.all_total}"
                f" | wrong field {table.wrong_field}, wrong unit {table.wrong_unit}, missed {table.missed},"
                f" false mappings {len(table.false_mappings)}"
            )
            for name in table.false_mappings:
                lines.append(f"    false mapping: {name!r}")
        if self.tables:
            found = sum(table.mapped_found for table in self.tables)
            total = sum(table.mapped_total for table in self.tables)
            correct = sum(table.all_correct for table in self.tables)
            columns = sum(table.all_total for table in self.tables)
            lines.append(
                f"Total over {len(self.tables)} table(s): mapped columns found {found} of {total}"
                f" | all columns correct {correct} of {columns}"
            )
        else:
            lines.append("No table was scored.")
        lines.extend(f"Skipped: {line}" for line in self.skipped)
        lines.extend(f"Error: {line}" for line in self.errors)
        return "\n".join(lines)


def _compare(source_id, gold, proposal) -> TableScore:
    score = TableScore(source_id=source_id)
    proposed = {column.source_column: column for column in proposal.columns}
    for wanted in gold.columns:
        got = proposed[wanted.source_column]
        score.all_total += 1
        if wanted.target_field is None:
            if got.target_field is None:
                score.all_correct += 1
            else:
                score.false_mappings.append(wanted.source_column)
            continue
        score.mapped_total += 1
        if got.target_field is None:
            score.missed += 1
        elif got.target_field != wanted.target_field:
            score.wrong_field += 1
        elif got.unit != wanted.unit:
            score.wrong_unit += 1
        else:
            score.mapped_found += 1
            score.all_correct += 1
    return score


def score(data_dir) -> ScoreReport:
    report = ScoreReport()
    gold_ids = sorted(path.stem for path in store.gold_dir(data_dir).glob("*.json"))
    proposal_ids = sorted({path.name.split(".")[0] for path in store.proposals_dir(data_dir).glob("*.json")})

    for source_id in gold_ids:
        copy = store.latest_proposal(data_dir, source_id)
        if copy is None:
            report.skipped.append(f"{source_id} has a gold mapping but no proposal yet.")
            continue
        try:
            gold = store.read_mapping(store.gold_dir(data_dir) / f"{source_id}.json")
            proposal = store.read_mapping(copy)
        except (ValueError, ValidationError) as error:
            report.errors.append(f"{source_id}: a file does not fit the mapping shape. {error}")
            continue
        gold_columns = {column.source_column for column in gold.columns}
        proposal_columns = {column.source_column for column in proposal.columns}
        if gold_columns != proposal_columns:
            differing = ", ".join(sorted(gold_columns ^ proposal_columns))
            report.errors.append(f"{source_id}: the gold mapping and the proposal list different columns: {differing}")
            continue
        report.tables.append(_compare(source_id, gold, proposal))

    for source_id in proposal_ids:
        if source_id not in gold_ids:
            report.skipped.append(f"{source_id} has a proposal but no gold mapping, so it is not scored.")
    return report
