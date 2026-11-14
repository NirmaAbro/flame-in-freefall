"""Task T9. Stub: the test rows as a CSV file, on sample data."""
import csv
import io

from fastapi import APIRouter, Response

from .. import fixtures

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
def export_tests_csv():
    """One line per test. A value that is not reported is an empty cell."""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=COLUMNS, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for row in fixtures.tests():
        out = dict(row)
        # Serialise the flags list as semicolon-joined; empty list → empty cell
        flags = out.get("flags") or []
        out["flags"] = ";".join(flags) if flags else ""
        writer.writerow(out)
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="tests.csv"'},
    )
