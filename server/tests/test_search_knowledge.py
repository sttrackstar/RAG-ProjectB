import pytest
import requests

from tools.search_knowledge import search_knowledge


class FakeResponse:
    """Stands in for a requests.Response in tests."""

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
    """Use fixed settings so tests never depend on your real .env."""
    monkeypatch.setenv("ANYTHINGLLM_BASE_URL", "http://fake-llm:3001")
    monkeypatch.setenv("ANYTHINGLLM_API_KEY", "test-key")
    monkeypatch.setenv("ANYTHINGLLM_WORKSPACE", "test-ws")
    monkeypatch.setenv("TOOL_TIMEOUT_SECONDS", "5")


def test_returns_answer_and_unique_sources(monkeypatch):
    calls = {}

    def fake_post(url, json, headers, timeout):
        calls.update(url=url, json=json, headers=headers, timeout=timeout)
        return FakeResponse(json_data={
            "textResponse": "Nimbus Pro is $8 per month.",
            "sources": [{"title": "nimbus-faq.txt"}, {"title": "nimbus-faq.txt"}],
        })

    monkeypatch.setattr(requests, "post", fake_post)

    result = search_knowledge("How much does Nimbus Pro cost?")

    assert result == {"answer": "Nimbus Pro is $8 per month.", "sources": ["nimbus-faq.txt"]}
    assert calls["url"] == "http://fake-llm:3001/api/v1/workspace/test-ws/chat"
    assert calls["json"] == {"message": "How much does Nimbus Pro cost?", "mode": "query"}
    assert calls["headers"] == {"Authorization": "Bearer test-key"}
    assert calls["timeout"] == 5.0


def test_empty_query_returns_error_without_calling_service(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("should not call the service")

    monkeypatch.setattr(requests, "post", fail_if_called)

    assert "error" in search_knowledge("   ")


def test_timeout_returns_error(monkeypatch):
    def fake_post(*args, **kwargs):
        raise requests.Timeout()

    monkeypatch.setattr(requests, "post", fake_post)

    assert "timed out" in search_knowledge("anything")["error"]


def test_service_down_returns_error(monkeypatch):
    def fake_post(*args, **kwargs):
        raise requests.ConnectionError()

    monkeypatch.setattr(requests, "post", fake_post)

    assert "unreachable" in search_knowledge("anything")["error"]


def test_bad_api_key_returns_error(monkeypatch):
    monkeypatch.setattr(requests, "post", lambda *a, **k: FakeResponse(status_code=401))

    assert "API key" in search_knowledge("anything")["error"]


def test_non_json_response_returns_error(monkeypatch):
    monkeypatch.setattr(requests, "post", lambda *a, **k: FakeResponse(json_data=None))

    assert "non-JSON" in search_knowledge("anything")["error"]
