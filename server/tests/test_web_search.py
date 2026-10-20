import pytest
import requests

from tools.registry import TOOLS, tool_schemas
from tools.web_search import web_search


class FakeResponse:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self.json_data = json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        if self.json_data is None:
            raise ValueError("not JSON")
        return self.json_data


@pytest.fixture(autouse=True)
def fake_env(monkeypatch):
    monkeypatch.setenv("TOOL_TIMEOUT_SECONDS", "5")


def test_returns_results_sorted_by_rank_and_sends_correct_request(monkeypatch):
    calls = {}

    def fake_get(url, params, headers, timeout):
        calls.update(url=url, params=params, headers=headers, timeout=timeout)
        return FakeResponse(json_data={"query": {"pages": [
            {"index": 2, "title": "Milvus", "fullurl": "https://en.wikipedia.org/wiki/Milvus", "extract": "Second."},
            {"index": 1, "title": "Vector database", "fullurl": "https://en.wikipedia.org/wiki/Vector_database", "extract": "First."},
        ]}})

    monkeypatch.setattr(requests, "get", fake_get)

    result = web_search("vector database")

    assert result == {"results": [
        {"title": "Vector database", "url": "https://en.wikipedia.org/wiki/Vector_database", "snippet": "First."},
        {"title": "Milvus", "url": "https://en.wikipedia.org/wiki/Milvus", "snippet": "Second."},
    ]}
    assert calls["url"] == "https://en.wikipedia.org/w/api.php"
    assert calls["params"]["gsrsearch"] == "vector database"
    assert "User-Agent" in calls["headers"]
    assert calls["timeout"] == 5.0


def test_no_matches_returns_empty_results(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResponse(json_data={"batchcomplete": True}))

    assert web_search("asdfqwerzxcv") == {"results": []}


def test_empty_query_returns_error_without_calling_service(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("should not call the service")

    monkeypatch.setattr(requests, "get", fail_if_called)

    assert "error" in web_search("  ")


def test_timeout_returns_error(monkeypatch):
    def fake_get(*args, **kwargs):
        raise requests.Timeout()

    monkeypatch.setattr(requests, "get", fake_get)

    assert "timed out" in web_search("anything")["error"]


def test_no_internet_returns_error(monkeypatch):
    def fake_get(*args, **kwargs):
        raise requests.ConnectionError()

    monkeypatch.setattr(requests, "get", fake_get)

    assert "unreachable" in web_search("anything")["error"]


def test_http_error_returns_error(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResponse(status_code=503))

    assert "HTTP 503" in web_search("anything")["error"]


def test_unexpected_response_returns_error(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResponse(json_data=None))

    assert "unexpected" in web_search("anything")["error"]


def test_web_search_is_registered_for_the_agent():
    assert TOOLS["web_search"]["function"] is web_search
    names = [schema["function"]["name"] for schema in tool_schemas()]
    assert "web_search" in names
