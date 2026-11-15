from types import SimpleNamespace

from fastapi.testclient import TestClient

from app import schemas
from app.main import app


API = "/api/v1"
client = TestClient(app)


class FakeQuery:
    def __init__(self, table, rows):
        self.table_name = table
        self.rows = rows
        self.filtered_investigation_id = None
        self.start = 0
        self.end = None

    def select(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def range(self, start, end):
        self.start = start
        self.end = end
        return self

    def eq(self, column, value):
        if column == "investigation_id":
            self.filtered_investigation_id = value
        return self

    def execute(self):
        rows = self.rows
        if self.filtered_investigation_id is not None:
            rows = [
                row
                for row in rows
                if row["investigation_id"] == self.filtered_investigation_id
            ]
        end = None if self.end is None else self.end + 1
        return SimpleNamespace(
            data=rows[self.start:end],
            count=len(rows),
        )


class FakeSupabase:
    def __init__(self):
        self.rows = {
            "investigations": [
                {
                    "id": "PSI-25",
                    "files": ["bass.csv"],
                    "publications": [],
                    "ingested_at": "2026-11-12",
                    "topic_tags": ["flammability"],
                },
                {
                    "id": "PSI-69",
                    "files": ["flex.csv"],
                    "publications": ["doi"],
                    "ingested_at": "2026-11-11",
                    "topic_tags": ["flammability", "extinction"],
                },
                {
                    "id": "PSI-70",
                    "files": [],
                    "publications": [],
                    "ingested_at": None,
                    "topic_tags": [],
                },
            ],
            "tests": [
                {"investigation_id": "PSI-25"},
                {"investigation_id": "PSI-25"},
                {"investigation_id": "PSI-69"},
                {"investigation_id": "PSI-69"},
                {"investigation_id": "PSI-69"},
            ],
            "habitats": [{"id": "a"}, {"id": "b"}, {"id": "c"}, {"id": "d"}],
        }

    def table(self, name):
        return FakeQuery(name, self.rows[name])


def test_dashboard_fixture_mode_has_source_header(monkeypatch):
    import app.data_access as data_access

    monkeypatch.setattr(data_access, "has_credentials", lambda: False)
    response = client.get(f"{API}/dashboard/summary")

    assert response.status_code == 200
    assert response.headers["x-data-source"] == "fixtures (sample)"
    body = response.json()
    schemas.DashboardSummary.model_validate(body)
    assert body["dataset_note"].startswith("Sample data")


def test_dashboard_supabase_counts_and_source_header(monkeypatch):
    import app.data_access as data_access

    monkeypatch.setattr(data_access, "has_credentials", lambda: True)
    monkeypatch.setattr(data_access, "_get_client", lambda: FakeSupabase())
    response = client.get(f"{API}/dashboard/summary")
    body = response.json()

    assert response.status_code == 200
    assert response.headers["x-data-source"] == "supabase"
    assert body["investigation_count"] == 3
    assert body["test_count"] == 5
    assert body["habitat_count"] == 4
    assert body["file_count"] == 2
    assert body["publication_count"] == 1
    assert body["tests_by_investigation"] == [
        {"label": "PSI-25", "count": 2},
        {"label": "PSI-69", "count": 3},
        {"label": "PSI-70", "count": 0},
    ]
    assert body["featured_ids"] == []


def test_dashboard_supabase_failure_returns_503_without_fixture_fallback(monkeypatch):
    import app.data_access as data_access

    monkeypatch.setattr(data_access, "has_credentials", lambda: True)

    def failing_client():
        raise RuntimeError("connection refused")

    monkeypatch.setattr(data_access, "_get_client", failing_client)
    response = client.get(f"{API}/dashboard/summary")

    assert response.status_code == 503
    assert response.headers.get("x-data-source") is None
