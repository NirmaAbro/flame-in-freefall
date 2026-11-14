import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "live: the test calls the real model and needs LLM_API_KEY")


@pytest.fixture(autouse=True)
def _force_fixture_data_for_rank(monkeypatch):
    """Patch the rank router so route tests always run against fixture data.

    Without this, TestClient connects to Supabase when credentials are present
    in .env, and the fixture habitat IDs (moon-base, spacesuit) are not in the
    real DB, causing 404s.  Route tests are explicitly offline-only.
    """
    import app.routers.rank as _rank_router

    monkeypatch.setattr(_rank_router, "_load_data", _rank_router._load_from_fixtures)
