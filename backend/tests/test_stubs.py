"""Checks for task T0: every route answers, and every answer has the agreed shape.

Run from the backend folder:  python -m pytest
"""
import csv
import io

import pytest
from fastapi.testclient import TestClient

from app import db, llm, schemas
from app.main import app

API = "/api/v1"
client = TestClient(app)


def get_ok(path, **params):
    response = client.get(API + path, params=params)
    assert response.status_code == 200, response.text
    return response.json()


def post_ok(path, body):
    response = client.post(API + path, json=body)
    assert response.status_code == 200, response.text
    return response.json()


def test_health():
    assert get_ok("/health") == {"status": "ok"}


# ---------- The eight routes the frontend already calls ----------


def test_dashboard_summary_counts_the_sample_records():
    body = get_ok("/dashboard/summary")
    schemas.DashboardSummary.model_validate(body)
    assert body["investigation_count"] == 14
    assert len(body["counts_by_topic"]) == 7


def test_filters_have_the_four_lists():
    body = get_ok("/filters")
    schemas.FilterOptions.model_validate(body)
    assert len(body["topics"]) == 7
    assert len(body["materials"]) == 4


def test_investigation_list_is_paged():
    first = get_ok("/investigations")
    schemas.Paginated[schemas.InvestigationListItem].model_validate(first)
    assert (first["page"], first["page_size"], first["total"]) == (1, 6, 14)
    assert len(first["items"]) == 6
    last = get_ok("/investigations", page=3, page_size=6)
    assert len(last["items"]) == 2
    assert not {item["id"] for item in first["items"]} & {item["id"] for item in last["items"]}


def test_investigation_list_accepts_the_frontend_filters():
    body = get_ok(
        "/investigations",
        q="flame",
        topic="Fire suppression",
        platform="International Space Station",
        material="Solid",
        measurement="Flame spread observation",
        sort="relevance",
        page=1,
        page_size=20,
    )
    schemas.Paginated[schemas.InvestigationListItem].model_validate(body)


def test_investigation_detail_and_missing_record():
    body = get_ok("/investigations/psi-bass-ii")
    schemas.Investigation.model_validate(body)
    assert body["acronym"] == "BASS-II"
    assert body["data_status"] == "sample"
    assert client.get(API + "/investigations/no-such-record").status_code == 404


def test_missing_values_are_null_not_empty():
    body = get_ok("/investigations/psi-same")
    assert body["platform"] is None
    assert body["doi"] is None


def test_compare_has_one_cell_per_requested_record():
    ids = ["psi-bass", "psi-flex"]
    body = post_ok("/compare", {"investigation_ids": ids})
    schemas.CompareResponse.model_validate(body)
    assert [item["id"] for item in body["investigations"]] == ids
    assert all(set(row["cells"]) == set(ids) for row in body["rows"])


def test_coverage_matrix_is_topic_by_fuel_class():
    body = get_ok("/analytics/coverage")
    schemas.CoverageResponse.model_validate(body)
    assert len(body["cells"]) == len(body["rows"]) * len(body["columns"]) == 28
    assert all(cell["count"] == len(cell["investigation_ids"]) for cell in body["cells"])


def test_ai_search_returns_only_the_filters_it_set():
    body = post_ok("/ai/search", {"question": "flame spread"})
    schemas.AiSearchIntent.model_validate(body)
    assert body["interpreted_as"] == {"q": "flame spread"}


def test_ai_ask_cites_only_the_given_records():
    body = post_ok("/ai/ask", {"question": "Compare these", "investigation_ids": ["psi-flex", "nope"]})
    schemas.AiAnswer.model_validate(body)
    assert [citation["investigation_id"] for citation in body["citations"]] == ["psi-flex"]
    without_ids = post_ok("/ai/ask", {"question": "What is known about oxygen?"})
    assert without_ids["citations"] == []


# ---------- The new routes ----------


def test_test_rows_and_their_filter():
    rows = get_ok("/tests")
    assert len(rows) == 6
    for row in rows:
        schemas.TestRow.model_validate(row)
    flex = get_ok("/tests", investigation_id="psi-flex")
    assert {row["investigation_id"] for row in flex} == {"psi-flex"}
    one = get_ok("/tests/psi-flex-1")
    assert one["raw"]["Ambient pressure; mmHg"] == "757.7"
    assert client.get(API + "/tests/no-such-test").status_code == 404


def test_sample_test_rows_point_at_sample_records():
    record_ids = {record["id"] for record in get_ok("/investigations", page_size=100)["items"]}
    assert {row["investigation_id"] for row in get_ok("/tests")} <= record_ids


def test_habitats():
    habitats = get_ok("/habitats")
    for habitat in habitats:
        schemas.Habitat.model_validate(habitat)
    assert {habitat["id"] for habitat in habitats} == {"moon-base", "spacesuit"}


def test_csv_export_has_one_line_per_test_and_empty_cells_for_missing_values():
    response = client.get(API + "/export/tests.csv")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    lines = list(csv.DictReader(io.StringIO(response.text)))
    assert len(lines) == 6
    assert lines[0]["pressure_kpa"] == ""
    assert lines[3]["pressure_kpa"] == "101.02"


def test_rank_needs_a_known_habitat():
    body = get_ok("/rank", habitat="moon-base")
    schemas.RankResponse.model_validate(body)
    assert len(body["items"]) == 14
    assert client.get(API + "/rank", params={"habitat": "nowhere"}).status_code == 404
    assert client.get(API + "/rank").status_code == 422


def test_variables_stub_counts_the_tests():
    body = get_ok("/investigations/psi-bass-ii/variables")
    schemas.VariablesResponse.model_validate(body)
    assert body["test_count"] == 3
    assert client.get(API + "/investigations/no-such-record/variables").status_code == 404


# ---------- Settings, database and model ----------


def test_frontend_origin_is_allowed():
    response = client.get(API + "/health", headers={"Origin": "http://localhost:3000"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_database_without_settings_raises(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_KEY", raising=False)
    with pytest.raises(db.DatabaseNotConfigured):
        db.get_supabase()


def test_model_without_key_raises(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    with pytest.raises(llm.LLMUnavailable):
        llm.complete("hello")
