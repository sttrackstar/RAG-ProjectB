import pytest
import requests

from llm import generate


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


SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "search_knowledge",
        "description": "Search the internal knowledge base",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
    },
}
USER_MESSAGES = [{"role": "user", "content": "How much does Nimbus Pro cost?"}]


@pytest.fixture(autouse=True)
def fake_env(monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://fake-ollama:11434")
    monkeypatch.setenv("AGENT_MODEL", "test-model")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "30")


def test_returns_tool_calls_and_sends_correct_request(monkeypatch):
    calls = {}
    reply = {
        "role": "assistant",
        "content": "",
        "tool_calls": [{"function": {"name": "search_knowledge", "arguments": {"query": "Nimbus Pro cost"}}}],
    }

    def fake_post(url, json, timeout):
        calls.update(url=url, json=json, timeout=timeout)
        return FakeResponse(json_data={"message": reply})

    monkeypatch.setattr(requests, "post", fake_post)

    result = generate(USER_MESSAGES, [SEARCH_TOOL])

    assert result["type"] == "tool_calls"
    assert result["tool_calls"] == [{"name": "search_knowledge", "arguments": {"query": "Nimbus Pro cost"}}]
    assert result["message"] == reply
    assert calls["url"] == "http://fake-ollama:11434/api/chat"
    assert calls["json"] == {"model": "test-model", "messages": USER_MESSAGES, "stream": False, "tools": [SEARCH_TOOL]}
    assert calls["timeout"] == 30.0


def test_decodes_string_arguments(monkeypatch):
    reply = {"role": "assistant", "content": "",
             "tool_calls": [{"function": {"name": "search_knowledge", "arguments": '{"query": "x"}'}}]}
    monkeypatch.setattr(requests, "post", lambda *a, **k: FakeResponse(json_data={"message": reply}))

    result = generate(USER_MESSAGES, [SEARCH_TOOL])

    assert result["tool_calls"][0]["arguments"] == {"query": "x"}


def test_returns_final_answer_and_omits_tools_when_none(monkeypatch):
    calls = {}

    def fake_post(url, json, timeout):
        calls["json"] = json
        return FakeResponse(json_data={"message": {"role": "assistant", "content": "Hi there friend"}})

    monkeypatch.setattr(requests, "post", fake_post)

    result = generate([{"role": "user", "content": "Say hi"}])

    assert result["type"] == "final"
    assert result["content"] == "Hi there friend"
    assert "tools" not in calls["json"]


def test_timeout_returns_error(monkeypatch):
    def fake_post(*args, **kwargs):
        raise requests.Timeout()

    monkeypatch.setattr(requests, "post", fake_post)

    result = generate(USER_MESSAGES)

    assert result["type"] == "error"
    assert "timed out" in result["error"]


def test_ollama_down_returns_error(monkeypatch):
    def fake_post(*args, **kwargs):
        raise requests.ConnectionError()

    monkeypatch.setattr(requests, "post", fake_post)

    assert "unreachable" in generate(USER_MESSAGES)["error"]


def test_http_error_returns_error(monkeypatch):
    monkeypatch.setattr(requests, "post", lambda *a, **k: FakeResponse(status_code=500))

    assert "HTTP 500" in generate(USER_MESSAGES)["error"]


def test_unexpected_response_returns_error(monkeypatch):
    monkeypatch.setattr(requests, "post", lambda *a, **k: FakeResponse(json_data={"oops": True}))

    assert generate(USER_MESSAGES)["type"] == "error"
