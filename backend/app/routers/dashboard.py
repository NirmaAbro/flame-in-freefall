"""Task T3. Stub: the dashboard summary, counted from sample data."""
from fastapi import APIRouter

from .. import fixtures
from ..schemas import DashboardSummary

router = APIRouter(tags=["records"])


@router.get("/dashboard/summary", response_model=DashboardSummary)
def get_dashboard_summary():
    records = fixtures.investigations()
    return {
        "investigation_count": len(records),
        "file_count": sum(len(record["files"]) for record in records),
        "publication_count": sum(len(record["publications"]) for record in records),
        "last_ingestion_date": max(record["ingested_at"] for record in records),
        "counts_by_topic": [
            {"label": topic, "count": sum(topic in record["topic_tags"] for record in records)}
            for topic in fixtures.meta()["topics"]
        ],
        "featured_ids": fixtures.meta()["featured_ids"],
        "dataset_note": "Sample data served by the backend stubs. It is not verified against PSI.",
    }
