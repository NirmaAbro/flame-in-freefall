from copy import deepcopy

from fastapi.testclient import TestClient

from app import fixtures
from app.main import app


client = TestClient(app)


class _Query:
    def __init__(self, rows):
        self.rows = deepcopy(rows)
        self.filters = []
        self.or_conditions = None

    def select(self, *args, **kwargs):
        return self

    def or_(self, expression):
        conditions = []
        for part in expression.split(","):
            tokens = part.split(".ilike.")
            if len(tokens) == 2:
                col, val = tokens[0].strip(), tokens[1].strip().lower()
                conditions.append((col, val))
        self.or_conditions = conditions
        return self

    def eq(self, field, value):
        self.filters.append((field, value))
        return self

    def ilike(self, *args, **kwargs):
        return self

    def order(self, *args, **kwargs):
        return self

    def range(self, start, end):
        self.rows = self.rows[start : end + 1]
        return self

    def execute(self):
        rows = self.rows
        if self.or_conditions is not None:
            rows = [
                row for row in rows
                if any(
                    val == str(row.get(col) or "").lower() or val in str(row.get(col) or "").lower()
                    for col, val in self.or_conditions
                )
            ]
        if self.filters:
            rows = [
                row for row in rows
                if all(row.get(field) == value for field, value in self.filters)
            ]

        class _Response:
            data = rows
            count = len(rows)

        return _Response()


class _Client:
    def __init__(self):
        investigation = deepcopy(fixtures.investigations()[1])
        investigation.update({"id": "PSI-25", "source_id": "PSI-25", "acronym": "BASS-II"})
        self.investigations = [investigation]
        self.tests = [
            {
                **row,
                "investigation_id": "PSI-25",
                "id": row["id"].replace("psi-bass-ii", "PSI-25"),
            }
            for row in fixtures.tests()[:3]
        ]

    def table(self, name):
        return _Query(self.investigations if name == "investigations" else self.tests)


def test_investigation_aliases_return_the_same_canonical_record(monkeypatch):
    import app.data_access as data_access

    monkeypatch.setattr(data_access, "has_credentials", lambda: True)
    monkeypatch.setattr(data_access, "_get_client", _Client)

    responses = [
        client.get("/api/v1/investigations/PSI-25"),
        client.get("/api/v1/investigations/psi-25"),
        client.get("/api/v1/investigations/BASS-II"),
    ]

    assert [response.status_code for response in responses] == [200, 200, 200]
    assert {response.json()["id"] for response in responses} == {"PSI-25"}
    for response in responses:
        assert response.headers.get("x-data-source") == "supabase"


def test_test_filter_accepts_investigation_aliases(monkeypatch):
    import app.data_access as data_access

    monkeypatch.setattr(data_access, "has_credentials", lambda: True)
    monkeypatch.setattr(data_access, "_get_client", _Client)

    for alias in ("PSI-25", "psi-25", "BASS-II"):
        response = client.get("/api/v1/tests", params={"investigation_id": alias})
        assert response.status_code == 200
        assert response.json()["total"] == 3
        assert {row["investigation_id"] for row in response.json()["items"]} == {"PSI-25"}
        assert response.headers.get("x-data-source") == "supabase"


def test_unknown_investigation_alias_remains_404(monkeypatch):
    import app.data_access as data_access

    monkeypatch.setattr(data_access, "has_credentials", lambda: True)
    monkeypatch.setattr(data_access, "_get_client", _Client)

    response = client.get("/api/v1/investigations/unknown-id")

    assert response.status_code == 404


def test_fixture_investigation_aliases_return_the_same_canonical_record(monkeypatch):
    import app.data_access as data_access

    monkeypatch.setattr(data_access, "has_credentials", lambda: False)

    responses = [
        client.get("/api/v1/investigations/PSI-25"),
        client.get("/api/v1/investigations/psi-25"),
        client.get("/api/v1/investigations/BASS-II"),
    ]

    assert [response.status_code for response in responses] == [200, 200, 200]
    assert {response.json()["id"] for response in responses} == {"psi-bass-ii"}
    assert all(
        response.headers.get("x-data-source") == "fixtures (sample)"
        for response in responses
    )
    assert client.get("/api/v1/investigations/not-a-real-id").status_code == 404


def test_fixture_test_filter_accepts_investigation_aliases(monkeypatch):
    import app.data_access as data_access

    monkeypatch.setattr(data_access, "has_credentials", lambda: False)

    for alias in ("PSI-25", "psi-25", "BASS-II"):
        response = client.get(
            "/api/v1/tests",
            params={"investigation_id": alias},
        )
        assert response.status_code == 200
        assert response.json()["total"] == 3
        assert {
            row["investigation_id"] for row in response.json()["items"]
        } == {"psi-bass-ii"}

    unknown = client.get(
        "/api/v1/tests",
        params={"investigation_id": "not-a-real-id"},
    )
    assert unknown.status_code == 200
    assert unknown.json()["total"] == 0


def test_variables_accepts_investigation_aliases(monkeypatch):
    import app.data_access as data_access

    monkeypatch.setattr(data_access, "has_credentials", lambda: True)
    monkeypatch.setattr(data_access, "_get_client", _Client)

    for alias in ("PSI-25", "psi-25", "BASS-II"):
        response = client.get(f"/api/v1/investigations/{alias}/variables")
        assert response.status_code == 200
        assert response.headers.get("x-data-source") == "supabase"
        assert response.json()["investigation_id"] == "PSI-25"

    unknown = client.get("/api/v1/investigations/unknown-id/variables")
    assert unknown.status_code == 404
