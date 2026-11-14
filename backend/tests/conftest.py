def pytest_configure(config):
    config.addinivalue_line("markers", "live: the test calls the real model and needs LLM_API_KEY")
