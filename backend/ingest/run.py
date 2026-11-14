"""Ingest runner for PSI Experimental Tables (task T2).

Usage (run from flame-in-freefall/backend/):
    python -m ingest.run --dry-run   # parse only; write CSV + report, no DB
    python -m ingest.run             # parse + load Supabase (falls back if no creds)

Row id: "{investigation_id}:{source_file}:{source_row}"
  - investigation_id: PSI id from the mapping file (e.g. "PSI-25")
  - source_file: basename of the raw CSV
  - source_row: 1-based data row index (first row below header = 1)

DataStatus: rows are marked "sample" (the only non-"verified" value in the
existing DataStatus enum). This signals that the data was parsed from a source
table but has NOT been hand-verified against the original PSI record.
See backend/app/schemas.py: DataStatus = Literal["sample", "verified"]
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Paths (resolved relative to this file so the module works from any cwd)
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent          # backend/ingest/
_BACKEND = _HERE.parent                          # backend/
_REPO = _BACKEND.parent                          # flame-in-freefall/
_DATA = _REPO / "data"
_RAW = _DATA / "raw"
_MAPPINGS = _DATA / "mappings"
_EXPORT = _DATA / "export"

# Add backend/ to sys.path so "from app.schemas import ..." works when running
# as `python -m ingest.run` from the backend/ directory.
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

# Load backend/.env before any os.getenv() call so that app/config.py
# (and therefore app/db.py) sees the credentials.  This is the only place
# dotenv is loaded; app/config.py and app/db.py remain the single source of
# truth — they still read from os.getenv(), which is now populated.
try:
    from dotenv import load_dotenv  # python-dotenv is in requirements.txt
    load_dotenv(dotenv_path=_BACKEND / ".env", override=False)
except ImportError:
    pass  # python-dotenv not installed; env vars must come from the shell

from app.schemas import TestRow  # noqa: E402  (after path fixup)
from ingest.parse import parse_cell  # noqa: E402
from ingest.reader import read_csv  # noqa: E402

# ---------------------------------------------------------------------------
# Which PSI ids to process, in order
# ---------------------------------------------------------------------------
PSI_IDS = ["PSI-25", "PSI-69", "PSI-68"]

# PSI ids whose raw file is a parameter-space summary (not per-test rows).
# Their investigation record is still upserted; no rows go into the tests table or CSV.
_SUMMARY_ONLY_IDS: frozenset[str] = frozenset({"PSI-68"})

# Mapping from PSI id to raw filename glob suffix
_RAW_GLOB: Dict[str, str] = {
    "PSI-25": "PSI-25_*",
    "PSI-69": "PSI-69_*",
    "PSI-68": "PSI-68_*",
}

# BASS-II specific: columns used for extra quality flags
_BASS2_FINAL_O2_COL = "Calibrated final O2 % by vol"
_BASS2_CO_COL = "Initial CO (ppm)"
_BASS2_O2_DROP_THRESHOLD = 5.0  # percentage points

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_raw_file(psi_id: str) -> Optional[Path]:
    pattern = _RAW_GLOB[psi_id]
    matches = list(_RAW.glob(pattern))
    return matches[0] if matches else None


def _load_mapping(psi_id: str) -> Dict:
    path = _MAPPINGS / f"{psi_id}.json"
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _bass2_extra_flags(
    row_dict: Dict[str, str],
    initial_o2: Optional[float],
    source_row: int,
) -> List[str]:
    """Return BASS-II-specific data-quality flags for a single row."""
    flags: List[str] = []

    # Flag large drop in O2 (> 5 pp)
    final_raw = row_dict.get(_BASS2_FINAL_O2_COL, "").strip()
    if final_raw and final_raw.lower() not in ("none", "n/a", "-", ""):
        try:
            final_o2 = float(final_raw)
            if initial_o2 is not None and (initial_o2 - final_o2) > _BASS2_O2_DROP_THRESHOLD:
                flags.append(
                    f"oxygen_pct (final O2): initial={initial_o2:.2f}% "
                    f"final={final_o2:.2f}% — drop of "
                    f"{initial_o2 - final_o2:.2f} pp exceeds threshold "
                    f"{_BASS2_O2_DROP_THRESHOLD} pp"
                )
        except ValueError:
            pass  # unparseable final O2 — already in raw; not our business here

    # Flag negative CO
    co_raw = row_dict.get(_BASS2_CO_COL, "").strip()
    if co_raw and co_raw.lower() not in ("none", "n/a", "-", ""):
        try:
            co_val = float(co_raw)
            if co_val < 0:
                flags.append(
                    f"Initial CO (ppm): value {co_val} is negative — "
                    "data quality flag, raw value kept"
                )
        except ValueError:
            pass

    return flags


# ---------------------------------------------------------------------------
# Core ingest logic
# ---------------------------------------------------------------------------


def ingest_file(
    psi_id: str,
    raw_path: Path,
    mapping: Dict,
) -> Tuple[List[TestRow], List[Dict[str, Any]]]:
    """Parse one raw file; return (test_rows, flag_records).

    flag_records are dicts for the report:
      {investigation_id, source_row, field, column, reason}
    """
    _headers, rows = read_csv(raw_path)
    source_file = raw_path.name
    fields: Dict[str, Dict] = mapping["fields"]

    test_rows: List[TestRow] = []
    flag_records: List[Dict[str, Any]] = []

    for data_row_index, row_dict in enumerate(rows, start=1):
        # Build the raw dict: all columns, stripped strings, Nones preserved
        raw: Dict[str, Optional[str]] = {
            k: (v.strip() if v.strip() else None)
            for k, v in row_dict.items()
        }

        row_flags: List[str] = []
        parsed: Dict[str, Any] = {}

        # PSI-68 is a parameter-space summary, not per-test rows.
        # Flag every row; set all numeric fields to None.
        if psi_id == "PSI-68":
            _psi68_flag = (
                "PSI-68: this file is a parameter-space summary table "
                "(one row per fuel type, not per test run). "
                "Numeric fields contain range strings and cannot be parsed "
                "as single values. All numeric fields set to null."
            )
            row_flags.append(_psi68_flag)
            flag_records.append({
                "investigation_id": psi_id,
                "source_row": data_row_index,
                "field": "structure",
                "column": "all numeric",
                "reason": _psi68_flag,
            })
            # Still parse text fields (fuel, diluent)
            for field_name, field_def in fields.items():
                col = field_def["column"]
                rule = field_def["parse"]
                if rule == "text":
                    cell = row_dict.get(col, "")
                    val, cell_flags = parse_cell(cell, field_name, col, rule, None)
                    parsed[field_name] = val
                    for cf in cell_flags:
                        row_flags.append(cf)
                        flag_records.append({
                            "investigation_id": psi_id,
                            "source_row": data_row_index,
                            "field": field_name,
                            "column": col,
                            "reason": cf,
                        })
                else:
                    parsed[field_name] = None
        else:
            # Normal per-test parsing
            for field_name, field_def in fields.items():
                col = field_def["column"]
                rule = field_def["parse"]
                unit = field_def.get("unit")
                cell = row_dict.get(col, "")
                val, cell_flags = parse_cell(cell, field_name, col, rule, unit)
                parsed[field_name] = val
                for cf in cell_flags:
                    row_flags.append(cf)
                    flag_records.append({
                        "investigation_id": psi_id,
                        "source_row": data_row_index,
                        "field": field_name,
                        "column": col,
                        "reason": cf,
                    })

        # BASS-II extra quality checks
        if psi_id == "PSI-25":
            extra = _bass2_extra_flags(
                row_dict, parsed.get("oxygen_pct"), data_row_index
            )
            for ef in extra:
                row_flags.append(ef)
                flag_records.append({
                    "investigation_id": psi_id,
                    "source_row": data_row_index,
                    "field": "data_quality",
                    "column": "multiple",
                    "reason": ef,
                })

        # Build row id
        row_id = f"{psi_id}:{source_file}:{data_row_index}"

        # Collect unmapped fields (None by default)
        test_row = TestRow(
            id=row_id,
            investigation_id=psi_id,
            test_label=parsed.get("test_label"),
            fuel=parsed.get("fuel"),
            geometry=None,
            oxygen_pct=parsed.get("oxygen_pct"),
            pressure_kpa=parsed.get("pressure_kpa"),
            flow_cm_s=parsed.get("flow_cm_s"),
            diluent=parsed.get("diluent"),
            outcome=parsed.get("outcome"),
            source_file=source_file,
            source_row=data_row_index,
            raw=raw,
            flags=row_flags,
            data_status="parsed",
        )
        test_rows.append(test_row)

    return test_rows, flag_records


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------

_CSV_COLUMNS = [
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


def _write_csv(all_rows: List[TestRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=_CSV_COLUMNS, extrasaction="ignore", lineterminator="\n"
        )
        writer.writeheader()
        for row in all_rows:
            d = row.model_dump()
            # None → empty string; flags list → semicolons
            out = {}
            for col in _CSV_COLUMNS:
                val = d.get(col)
                if val is None:
                    out[col] = ""
                elif isinstance(val, list):
                    out[col] = ";".join(val)
                else:
                    out[col] = val
            writer.writerow(out)


def _write_report(
    all_rows: List[TestRow],
    flag_records: List[Dict[str, Any]],
    per_file_rows: Dict[str, List[TestRow]],
    summary_only: Dict[str, int],
    path: Path,
) -> None:
    """Write the markdown report.

    summary_only: {psi_id: raw_row_count} for files that produced no test rows.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    numeric_fields = ["oxygen_pct", "pressure_kpa", "flow_cm_s"]

    lines: List[str] = []
    lines.append("# T2 Ingest Report\n")
    lines.append(
        f"Total test rows ingested: **{len(all_rows)}** "
        f"({sum(1 for r in all_rows if r.flags)} with flags)\n"
    )

    for psi_id, rows in per_file_rows.items():
        lines.append(f"\n## {psi_id}  ({len(rows)} rows)\n")
        lines.append("| Field | Parsed | None |")
        lines.append("|---|---|---|")
        text_fields = ["test_label", "fuel", "diluent", "outcome"]
        for f in text_fields + numeric_fields:
            parsed_count = sum(1 for r in rows if getattr(r, f) is not None)
            none_count = len(rows) - parsed_count
            lines.append(f"| {f} | {parsed_count} | {none_count} |")

    for psi_id, raw_count in summary_only.items():
        lines.append(f"\n## {psi_id}  (parameter-space summary — 0 test rows loaded)\n")
        lines.append(
            f"The raw file for {psi_id} contains {raw_count} parameter-space rows "
            "(one row per fuel type, not per test run). "
            "No rows were added to the tests table or the CSV export. "
            "The investigation record is kept in `data/investigations.json` with a "
            "`summary` field quoting the parameter ranges as written in the source table.\n"
        )

    file_flags = [fr for fr in flag_records if fr["investigation_id"] in per_file_rows]
    if file_flags:
        lines.append("\n## Flagged cells\n")
        lines.append("| Investigation | Row | Field | Column | Reason |")
        lines.append("|---|---|---|---|---|")
        for fr in file_flags:
            reason = fr["reason"].replace("|", "\\|")
            lines.append(
                f"| {fr['investigation_id']} | {fr['source_row']} "
                f"| {fr['field']} | {fr['column']} | {reason} |"
            )
    else:
        lines.append("\n*No flagged cells.*\n")

    with path.open("w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# Database loader
# ---------------------------------------------------------------------------


# Columns that exist in the investigations DB table (schema.sql).
# Keys present in investigations.json but absent here are silently dropped.
_INV_DB_COLUMNS = {
    "id", "source_id", "title", "acronym", "summary",
    "research_area", "project_type", "platform", "environment",
    "hardware", "hardware_family", "safety_function",
    "fuel_classes", "fuel_materials", "topic_tags", "measurement_types",
    "conditions", "files", "publications",
    "source_url", "doi", "source_updated_at", "ingested_at", "data_status",
}

import datetime as _datetime  # noqa: E402


def _load_investigations(supabase_client, investigations_path: Path) -> None:
    with investigations_path.open(encoding="utf-8") as fh:
        raw_records = json.load(fh)

    today = _datetime.date.today().isoformat()
    db_records = []
    for src in raw_records:
        rec: dict = {}
        # Rename psi_id -> source_id (psi_id is not a DB column)
        rec["source_id"] = src.get("psi_id") or src.get("source_id") or src["id"]
        # Copy all DB columns that are present in the JSON
        for col in _INV_DB_COLUMNS - {"source_id"}:
            if col in src:
                rec[col] = src[col]
        # Required NOT NULL columns — override None with safe defaults
        if not rec.get("source_url"):
            rec["source_url"] = ""          # empty string satisfies NOT NULL
        if not rec.get("ingested_at"):
            rec["ingested_at"] = today
        if not rec.get("data_status"):
            rec["data_status"] = "sample"
        # Drop any key that is not a DB column (e.g. 'psi_id', 'files', 'publications'
        # if the live table doesn't have them yet)
        db_records.append({k: v for k, v in rec.items() if k in _INV_DB_COLUMNS})

    for rec in db_records:
        supabase_client.table("investigations").upsert(
            rec, on_conflict="id"
        ).execute()
    print(f"  Upserted {len(db_records)} investigation records.")


def _load_tests(supabase_client, rows: List[TestRow], batch_size: int = 100) -> None:
    total = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        payload = [r.model_dump() for r in batch]
        # Serialise list fields to JSON-compatible types
        for rec in payload:
            rec["flags"] = rec["flags"]  # already a list; supabase-py handles JSONB
            rec["raw"] = rec["raw"]      # dict → JSONB
        supabase_client.table("tests").upsert(
            payload,
            on_conflict="investigation_id,source_file,source_row",
        ).execute()
        total += len(batch)
    print(f"  Upserted {total} test rows.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run(dry_run: bool = False) -> None:
    # test rows that go into the CSV and DB
    all_rows: List[TestRow] = []
    all_flags: List[Dict[str, Any]] = []
    # PSI ids with real per-test rows
    per_file_rows: Dict[str, List[TestRow]] = {}
    # PSI ids that are parameter-space summaries: {psi_id: raw_row_count}
    summary_only: Dict[str, int] = {}

    print("=" * 60)
    print(f"T2 Ingest  (dry_run={dry_run})")
    print("=" * 60)

    for psi_id in PSI_IDS:
        raw_path = _find_raw_file(psi_id)
        if raw_path is None:
            print(f"[SKIP] {psi_id}: no raw file found in {_RAW}")
            continue

        mapping_path = _MAPPINGS / f"{psi_id}.json"
        if not mapping_path.exists():
            print(f"[SKIP] {psi_id}: no mapping file at {mapping_path}")
            continue

        mapping = _load_mapping(psi_id)
        print(f"\n[{psi_id}]  {raw_path.name}")

        rows, flags = ingest_file(psi_id, raw_path, mapping)
        all_flags.extend(flags)

        if psi_id in _SUMMARY_ONLY_IDS:
            summary_only[psi_id] = len(rows)
            print(f"  {len(rows)} parameter-space rows — excluded from tests (summary-only)")
            _print_preview(rows[:5], mapping)
        else:
            per_file_rows[psi_id] = rows
            all_rows.extend(rows)
            flagged = sum(1 for r in rows if r.flags)
            print(f"  {len(rows)} data rows | {flagged} rows with flags")
            _print_preview(rows[:5], mapping)

    print(f"\nTotal test rows: {len(all_rows)}")

    # Write outputs
    csv_path = _EXPORT / "tests.csv"
    report_path = _EXPORT / "report.md"
    _write_csv(all_rows, csv_path)
    _write_report(all_rows, all_flags, per_file_rows, summary_only, report_path)
    print(f"\nWrote {csv_path}")
    print(f"Wrote {report_path}")

    # Database
    if not dry_run:
        investigations_path = _DATA / "investigations.json"
        try:
            # Import here (after sys.path is set) to avoid import-time error
            from app.db import DatabaseNotConfigured, get_supabase  # noqa: E402
            client = get_supabase()
            print("\nLoading Supabase...")
            _load_investigations(client, investigations_path)
            _load_tests(client, all_rows)
            print("Done.")
        except Exception as exc:  # DatabaseNotConfigured or supabase error
            print(
                f"\n[WARNING] Database load skipped: {exc}\n"
                "  Set SUPABASE_URL and SUPABASE_KEY in backend/.env to load.\n"
                "  CSV and report written successfully (dry-run outputs are valid)."
            )


def _print_preview(rows: List[TestRow], mapping: Dict) -> None:
    """Print 5 rows: source column → parsed field, side by side."""
    if not rows:
        return
    fields = mapping["fields"]
    for row in rows:
        print(f"  --- row {row.source_row} ---")
        for field_name, fdef in fields.items():
            col = fdef["column"]
            raw_val = row.raw.get(col, "(column missing)")
            parsed_val = getattr(row, field_name)
            print(f"    {col!r:50s} -> {field_name}={parsed_val!r}")
        if row.flags:
            for flag in row.flags:
                print(f"    FLAG: {flag}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="T2 PSI ingest")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and write outputs but do not load Supabase.",
    )
    args = parser.parse_args()
    run(dry_run=args.dry_run)
