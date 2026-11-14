import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "live: the test calls the real model and needs LLM_API_KEY")


@pytest.fixture(autouse=True)
def _force_fixture_data(monkeypatch):
    """Patch all data-access layers so every test runs on fixture data.

    - app.data_access.has_credentials → always False
      → all four T3 routes (investigations, tests, habitats, export) serve fixtures
    - app.routers.rank._load_data → _load_from_fixtures
      → rank route uses fixture habitats (moon-base, spacesuit), not the live DB

    Without this, TestClient connects to Supabase when credentials are present in
    .env.  Fixture IDs used by the stub tests (moon-base, psi-bass-ii, etc.) do
    not exist in the live DB and would return 404 / wrong counts.
    Route tests are explicitly offline-only.
    """
    import app.data_access as _da
    import app.routers.rank as _rank_router

    monkeypatch.setattr(_da, "has_credentials", lambda: False)
    monkeypatch.setattr(_rank_router, "_load_data", _rank_router._load_from_fixtures)
