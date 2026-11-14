"""Read a PSI Experimental Table (a CSV file)."""
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


class TableError(Exception):
    """The table file cannot be used as it is."""


@dataclass(frozen=True)
class Table:
    path: Path
    header: List[str]
    rows: List[Dict[str, str]]


def read_table(path) -> Table:
    """Read the header and the rows. A file that would lose data is refused."""
    path = Path(path)
    if not path.is_file():
        raise TableError(f"The table file was not found: {path.name}")
    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:  # utf-8-sig drops a byte-order mark
            lines = list(csv.reader(handle))
    except UnicodeDecodeError:
        raise TableError(f"{path.name} is not saved as UTF-8. Save it as UTF-8 and try again.") from None
    if not lines:
        raise TableError(f"The table file is empty: {path.name}")

    header = [name.strip() for name in lines[0]]
    body = lines[1:]
    # Drop unnamed columns at the end, but only when they hold no value.
    while header and not header[-1] and not any(len(line) >= len(header) and line[len(header) - 1].strip() for line in body):
        header.pop()
    unnamed = [str(position + 1) for position, name in enumerate(header) if not name]
    if unnamed:
        raise TableError(f"{path.name} has a column without a name (column {', '.join(unnamed)}).")
    repeated = sorted({name for name in header if header.count(name) > 1})
    if repeated:
        raise TableError(f"{path.name} has a repeated column name: {', '.join(repeated)}")

    rows = []
    for line in body:
        cells = [cell.strip() for cell in line[: len(header)]]
        if any(cells):
            rows.append(dict(zip(header, cells + [""] * (len(header) - len(cells)))))
    return Table(path=path, header=header, rows=rows)
