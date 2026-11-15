import httpx

from app import llm


def _response(status_code, content="hello", text=""):
    if status_code == 200:
        return httpx.Response(
            status_code,
            json={"choices": [{"message": {"content": content}}]},
        )
    return httpx.Response(status_code, content=(text or "error").encode())


def test_url_building_with_and_without_trailing_slash(monkeypatch):
    calls = []

    def fake_post(url, **kwargs):
        calls.append(url)
        return _response(200)

    monkeypatch.setenv("LLM_API_KEY", "secret")
    monkeypatch.setattr(llm.httpx, "post", fake_post)
    monkeypatch.setenv("LLM_BASE_URL", "https://example.test/api")
    assert llm.complete("system", "user") == "hello"
    monkeypatch.setenv("LLM_BASE_URL", "https://example.test/api/")
    assert llm.complete("system", "user") == "hello"
    assert calls == [
        "https://example.test/api/chat/completions",
        "https://example.test/api/chat/completions",
    ]


def test_empty_key_returns_none_without_request(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setattr(
        llm.httpx,
        "post",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError()),
    )
    assert llm.complete("system", "user") is None


def test_content_and_empty_content(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "secret")
    responses = iter([_response(200, "hello"), _response(200, None)])
    monkeypatch.setattr(llm.httpx, "post", lambda *args, **kwargs: next(responses))
    assert llm.complete("system", "user") == "hello"
    assert llm.complete("system", "user") is None


def test_429_retries_once(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "secret")
    responses = iter([_response(429, text="busy"), _response(200, "hello")])
    calls = []
    monkeypatch.setattr(
        llm.httpx,
        "post",
        lambda *args, **kwargs: (calls.append(1) or next(responses)),
    )
    monkeypatch.setattr(llm.time, "sleep", lambda seconds: None)
    assert llm.complete("system", "user") == "hello"
    assert len(calls) == 2


def test_401_does_not_retry(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "secret")
    calls = []
    monkeypatch.setattr(
        llm.httpx,
        "post",
        lambda *args, **kwargs: (calls.append(1) or _response(401, text="unauthorized")),
    )
    assert llm.complete("system", "user") is None
    assert len(calls) == 1


def test_timeout_returns_none(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "secret")
    monkeypatch.setattr(
        llm.httpx,
        "post",
        lambda *args, **kwargs: (_ for _ in ()).throw(httpx.TimeoutException("timed out")),
    )
    monkeypatch.setattr(llm.time, "sleep", lambda seconds: None)
    assert llm.complete("system", "user") is None


def test_key_never_appears_in_logs(monkeypatch, caplog):
    key = "secret-api-key"
    monkeypatch.setenv("LLM_API_KEY", key)
    monkeypatch.setattr(
        llm.httpx,
        "post",
        lambda *args, **kwargs: _response(401, text=f"bad key {key}"),
    )
    with caplog.at_level("WARNING"):
        assert llm.complete("system", "user") is None
    assert key not in caplog.text
