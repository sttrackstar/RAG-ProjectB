import json

import pytest

import agent
import observability
from app import app


def read_log(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_observe_logs_input_output_and_latency(temp_observability_log):
    @observability.observe("tool", describe_input=lambda x: {"x": x})
    def double(x):
        return {"value": x * 2}

    assert double(21) == {"value": 42}

    [event] = read_log(temp_observability_log)
    assert event["type"] == "tool"
    assert event["name"] == "double"
    assert event["input"] == {"x": 21}
    assert event["output"] == {"value": 42}
    assert event["latency_ms"] >= 0
    assert "time" in event


def test_observe_logs_exceptions_and_reraises(temp_observability_log):
    @observability.observe("tool")
    def broken():
        raise ValueError("boom")

    with pytest.raises(ValueError):
        broken()

    [event] = read_log(temp_observability_log)
    assert "boom" in event["error"]


def test_agent_run_logs_every_call_under_one_run_id(monkeypatch, temp_observability_log):
    replies = iter([
        {"type": "tool_calls", "tool_calls": [{"name": "search_knowledge", "arguments": {"query": "Nimbus"}}],
         "message": {"role": "assistant", "content": ""}},
        {"type": "final", "content": "$8/month", "message": {"role": "assistant", "content": "$8/month"}},
    ])
    monkeypatch.setattr(agent, "generate", observability.observe("llm")(lambda messages, tools: next(replies)))
    monkeypatch.setitem(agent.TOOLS, "search_knowledge", {
        "function": lambda query: {"answer": "stub", "sources": ["doc.txt"]},
        "schema": {"type": "function", "function": {"name": "search_knowledge"}},
    })

    result = agent.run_agent("How much is Nimbus Pro?")

    events = read_log(temp_observability_log)
    assert [e["type"] for e in events] == ["run_start", "llm", "tool", "llm", "run_end"]
    assert {e["run_id"] for e in events} == {result["run_id"]}
    assert events[2]["input"] == {"tool": "search_knowledge", "arguments": {"query": "Nimbus"}}
    assert events[-1]["answer"] == "$8/month"


def test_list_runs_and_get_run(monkeypatch):
    monkeypatch.setattr(agent, "generate", lambda messages, tools: {
        "type": "final", "content": "Hi", "message": {"role": "assistant", "content": "Hi"},
    })
    first = agent.run_agent("first question")
    second = agent.run_agent("second question")

    runs = observability.list_runs()

    assert [run["run_id"] for run in runs] == [second["run_id"], first["run_id"]]  # newest first
    assert runs[0]["goal"] == "second question"
    assert runs[0]["answer"] == "Hi"
    assert observability.get_run(first["run_id"])[0]["goal"] == "first question"


def test_logging_failure_never_breaks_the_caller(monkeypatch, tmp_path):
    monkeypatch.setenv("OBSERVABILITY_LOG", str(tmp_path))  # a folder, so writing fails

    @observability.observe("tool")
    def ok():
        return {"ok": True}

    assert ok() == {"ok": True}


def test_runs_endpoints(monkeypatch):
    monkeypatch.setattr(agent, "generate", lambda messages, tools: {
        "type": "final", "content": "Hi", "message": {"role": "assistant", "content": "Hi"},
    })
    run = agent.run_agent("hello")
    client = app.test_client()

    listing = client.get("/api/runs")
    detail = client.get(f"/api/runs/{run['run_id']}")
    missing = client.get("/api/runs/does-not-exist")

    assert listing.status_code == 200
    assert listing.get_json()[0]["run_id"] == run["run_id"]
    assert detail.status_code == 200
    assert [e["type"] for e in detail.get_json()["events"]] == ["run_start", "run_end"]
    assert missing.status_code == 404
