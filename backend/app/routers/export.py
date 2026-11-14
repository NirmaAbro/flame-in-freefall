"""Task T3. Export route — CSV download of the full test dataset."""
import csv
import io
from typing import Optional

from fastapi import APIRouter, Response

from ..data_access import iter_tests_csv

router = APIRouter(tags=["test rows"])

COLUMNS = [
    "id",
    "investigation_id",
    "test_label",
    "fuel",
    "geometry",
    "oxygen_pct",
    "pressure_kpa",
    "flow_cm_s",
    "diluent",
    "outcome",
    "source_file",
    "source_row",
    "flags",
    "data_status",
]


@router.get("/export/tests.csv")
def export_tests_csv(
    response: Response,
    investigation_id: Optional[str] = None,
):
    """CSV download: one line per test. NULL becomes an empty cell; flags join with semicolons."""
    row_iter, source = iter_tests_csv(investigation_id=investigation_id)

    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=COLUMNS,
        extrasaction="ignore",
        lineterminator="\n",
    )
    writer.writeheader()

    for row in row_iter:
        out: dict = {}
        for col in COLUMNS:
            val = row.get(col)
            if val is None:
                out[col] = ""
            elif isinstance(val, list):
                # flags: list of strings → semicolon-joined; empty list → ""
                out[col] = ";".join(str(v) for v in val) if val else ""
            else:
                out[col] = val
        writer.writerow(out)

    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="tests.csv"',
            "X-Data-Source": source,
        },
    )
