import pytest

import agent


def tool_call(name, arguments):
    """A fake generate() result asking for one tool."""
    return {
        "type": "tool_calls",
        "tool_calls": [{"name": name, "arguments": arguments}],
        "message": {"role": "assistant", "content": "", "tool_calls": []},
    }


def final(content):
    """A fake generate() result with a final answer."""
    return {"type": "final", "content": content, "message": {"role": "assistant", "content": content}}


def scripted_model(monkeypatch, replies):
    """Make generate() return `replies` in order, and record what it was sent."""
    sent = []

    def fake_generate(messages, tools):
        sent.append(list(messages))
        return replies[len(sent) - 1]

    monkeypatch.setattr(agent, "generate", fake_generate)
    return sent


@pytest.fixture(autouse=True)
def fake_tools(monkeypatch):
    fake_search = {
        "function": lambda query: {"answer": f"stub answer for {query}", "sources": ["doc.txt"]},
        "schema": {"type": "function", "function": {"name": "search_knowledge"}},
    }
    monkeypatch.setitem(agent.TOOLS, "search_knowledge", fake_search)
    monkeypatch.setenv("MAX_AGENT_STEPS", "3")


def test_tool_call_then_final_answer(monkeypatch):
    sent = scripted_model(monkeypatch, [tool_call("search_knowledge", {"query": "Nimbus Pro"}), final("$8/month")])

    result = agent.run_agent("How much is Nimbus Pro?")

    assert result["answer"] == "$8/month"
    assert result["steps"] == [{
        "type": "tool_call",
        "tool": "search_knowledge",
        "arguments": {"query": "Nimbus Pro"},
        "result": {"answer": "stub answer for Nimbus Pro", "sources": ["doc.txt"]},
    }]
    # The tool result was fed back to the model on the second call
    assert sent[1][-1]["role"] == "tool"
    assert "stub answer for Nimbus Pro" in sent[1][-1]["content"]


def test_final_answer_without_tools(monkeypatch):
    scripted_model(monkeypatch, [final("Hello!")])

    result = agent.run_agent("Say hello")

    assert result == {"answer": "Hello!", "steps": []}


def test_loop_stops_at_max_steps(monkeypatch):
    sent = scripted_model(monkeypatch, [tool_call("search_knowledge", {"query": "again"})] * 10)

    result = agent.run_agent("Loop forever")

    assert len(sent) == 3  # MAX_AGENT_STEPS
    assert len(result["steps"]) == 3
    assert "3 steps" in result["answer"]


def test_unknown_tool_is_reported_not_crashed(monkeypatch):
    scripted_model(monkeypatch, [tool_call("delete_everything", {}), final("I can't do that.")])

    result = agent.run_agent("Delete everything")

    assert result["steps"][0]["result"] == {"error": "Unknown tool: delete_everything"}
    assert result["answer"] == "I can't do that."


def test_wrong_argument_names_are_reported(monkeypatch):
    scripted_model(monkeypatch, [tool_call("search_knowledge", {"q": "oops"}), final("done")])

    result = agent.run_agent("anything")

    assert "Bad arguments" in result["steps"][0]["result"]["error"]


def test_model_error_returns_graceful_answer(monkeypatch):
    scripted_model(monkeypatch, [{"type": "error", "error": "Model timed out after 120s"}])

    result = agent.run_agent("anything")

    assert "couldn't reach the model" in result["answer"]
    assert result["steps"] == [{"type": "error", "error": "Model timed out after 120s"}]
