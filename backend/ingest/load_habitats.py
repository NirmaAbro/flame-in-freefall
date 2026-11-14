"""Load real, cited habitats into the Supabase habitats table (task T4 / data update).

Usage (run from flame-in-freefall/backend/):
    python -m ingest.load_habitats

What it does
------------
1. Reads data/habitats.json (the real-data file at the repo root; NOT the fixture).
2. Maps the JSON fields to the DB column names (see schema.sql).
3. Upserts all four rows on conflict id.
4. Deletes any rows whose id is in SAMPLE_IDS (the old sample placeholders).

The source field in data/habitats.json is a free-text citation string.
It is stored as a citation jsonb object so the DB column stays non-null:
    {"source_name": <text before the URL>, "source_url": <last URL in text>,
     "doi": null, "location": null, "accessed_at": "2026-11-14"}
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — mirrors ingest/run.py so we can reuse app/db
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent          # backend/ingest/
_BACKEND = _HERE.parent                          # backend/
_REPO = _BACKEND.parent                          # flame-in-freefall/

if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=_BACKEND / ".env", override=False)
except ImportError:
    pass

from app.db import DatabaseNotConfigured, get_supabase  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_DATA_HABITATS = _REPO / "data" / "habitats.json"

# IDs of the old placeholder rows that must be removed if present.
SAMPLE_IDS = ["moon-base", "spacesuit"]

_ACCESSED_AT = "2026-11-14"


# ---------------------------------------------------------------------------
# Field mapping helpers
# ---------------------------------------------------------------------------

def _extract_url(text: str) -> str:
    """Return the last https URL found in text, or '' if none."""
    urls = re.findall(r'https://\S+', text)
    return urls[-1].rstrip('.') if urls else ""


def _build_citation(source_text: str) -> dict:
    """Convert the free-text 'source' field into a citation jsonb object."""
    url = _extract_url(source_text)
    # Strip the URL (and any trailing whitespace) from the name part
    name = re.sub(r'https://\S+', '', source_text).strip().rstrip('.')
    return {
        "source_name": name or source_text,
        "source_url": url,
        "doi": None,
        "location": None,
        "accessed_at": _ACCESSED_AT,
    }


def _to_db_record(h: dict) -> dict:
    """Map data/habitats.json field names → habitats table column names."""
    citation = _build_citation(h.get("source", ""))
    return {
        "id": h["id"],
        "name": h["name"],
        "oxygen_pct_min": h.get("o2_min"),
        "oxygen_pct_max": h.get("o2_max"),
        "pressure_kpa_min": h.get("pressure_min_kpa"),
        "pressure_kpa_max": h.get("pressure_max_kpa"),
        "gravity": h.get("gravity"),
        "citation": citation,
        "data_status": "verified",
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run() -> None:
    print("Loading habitats into Supabase...")

    # 1. Read the data file
    habitats_raw = json.loads(_DATA_HABITATS.read_text(encoding="utf-8"))
    print(f"  Read {len(habitats_raw)} habitats from {_DATA_HABITATS.relative_to(_REPO)}")

    # 2. Map to DB records
    db_records = [_to_db_record(h) for h in habitats_raw]
    new_ids = [r["id"] for r in db_records]
    print(f"  IDs to upsert: {new_ids}")

    # 3. Connect
    try:
        client = get_supabase()
    except DatabaseNotConfigured as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)

    # 4. Upsert
    result = client.table("habitats").upsert(db_records, on_conflict="id").execute()
    print(f"  Upserted {len(result.data or [])} rows.")

    # 5. Delete old sample rows
    to_delete = [sid for sid in SAMPLE_IDS if sid not in new_ids]
    if to_delete:
        del_result = (
            client.table("habitats")
            .delete()
            .in_("id", to_delete)
            .execute()
        )
        deleted = len(del_result.data or [])
        print(f"  Deleted {deleted} sample row(s): {to_delete}")
    else:
        print("  No sample rows to delete.")

    # 6. Verify
    final = client.table("habitats").select("id, name, data_status").execute()
    print(f"\nHabitats table now contains {len(final.data or [])} row(s):")
    for row in final.data or []:
        print(f"  {row['id']:25s}  {row['name']:50s}  [{row['data_status']}]")


if __name__ == "__main__":
    run()
