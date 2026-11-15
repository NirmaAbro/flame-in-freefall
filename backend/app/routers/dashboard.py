"""Dashboard summary backed by the shared data-access layer."""
from collections import Counter
from typing import Any, Dict, List, Tuple

from fastapi import APIRouter, HTTPException, Response

from .. import data_access, fixtures
from ..schemas import DashboardSummary

router = APIRouter(tags=["records"])

DATASET_NOTE = (
    "Counts come from the PSI Experimental Tables indexed by this project "
    "(currently PSI-25 BASS-II and PSI-69 FLEX). This is not a complete PSI inventory."
)


def _fixture_summary() -> Dict[str, Any]:
    records = fixtures.investigations()
    tests = fixtures.tests()
    topics = fixtures.meta()["topics"]
    tests_by_investigation = Counter(row["investigation_id"] for row in tests)
    return {
        "investigation_count": len(records),
        "test_count": len(tests),
        "habitat_count": len(fixtures.habitats()),
        "file_count": sum(len(record.get("files") or []) for record in records),
        "publication_count": sum(
            len(record.get("publications") or []) for record in records
        ),
        "last_ingestion_date": max(
            (record.get("ingested_at") for record in records if record.get("ingested_at")),
            default=None,
        ),
        "counts_by_topic": [
            {
                "label": topic,
                "count": sum(topic in (record.get("topic_tags") or []) for record in records),
            }
            for topic in topics
        ],
        "tests_by_investigation": [
            {"label": investigation_id, "count": count}
            for investigation_id, count in sorted(tests_by_investigation.items())
        ],
        "featured_ids": fixtures.meta()["featured_ids"],
        "dataset_note": "Sample data served by the backend stubs. It is not verified against PSI.",
    }


def _supabase_summary() -> Tuple[Dict[str, Any], str]:
    records, investigation_count, source = data_access.list_investigations(
        page=1,
        page_size=1000,
    )
    _, test_count, test_source = data_access.list_tests(page=1, page_size=1)
    habitats, habitat_source = data_access.list_habitats()

    sources = {source, test_source, habitat_source}
    if sources != {data_access.DATA_SOURCE_SUPABASE}:
        raise HTTPException(
            status_code=503,
            detail="Database query returned inconsistent data sources.",
        )

    counts_by_topic = Counter(
        topic
        for record in records
        for topic in (record.get("topic_tags") or [])
    )
    tests_by_investigation: List[Dict[str, Any]] = []
    for record in records:
        _, count, investigation_source = data_access.list_tests(
            investigation_id=record["id"],
            page=1,
            page_size=1,
        )
        if investigation_source != data_access.DATA_SOURCE_SUPABASE:
            raise HTTPException(
                status_code=503,
                detail="Database query returned inconsistent data sources.",
            )
        tests_by_investigation.append({"label": record["id"], "count": count})

    ingestion_dates = [
        record.get("ingested_at")
        for record in records
        if record.get("ingested_at")
    ]
    featured_ids = [
        record["id"]
        for record in records
        if record.get("featured") is True
    ]
    return {
        "investigation_count": investigation_count,
        "test_count": test_count,
        "habitat_count": len(habitats),
        "file_count": sum(len(record.get("files") or []) for record in records),
        "publication_count": sum(
            len(record.get("publications") or []) for record in records
        ),
        "last_ingestion_date": max(ingestion_dates, default=None),
        "counts_by_topic": [
            {"label": topic, "count": count}
            for topic, count in sorted(counts_by_topic.items())
        ],
        "tests_by_investigation": sorted(
            tests_by_investigation,
            key=lambda item: str(item["label"]),
        ),
        "featured_ids": featured_ids,
        "dataset_note": DATASET_NOTE,
    }, source


@router.get("/dashboard/summary", response_model=DashboardSummary)
def get_dashboard_summary(response: Response):
    if not data_access.has_credentials():
        response.headers["X-Data-Source"] = data_access.DATA_SOURCE_FIXTURE
        return _fixture_summary()

    summary, source = _supabase_summary()
    response.headers["X-Data-Source"] = source
    return summary
