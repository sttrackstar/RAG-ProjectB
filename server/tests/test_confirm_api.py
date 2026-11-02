import pytest

import agent
from app import app


@pytest.fixture
def pending_note(monkeypatch):
    """A pending save_note action, with a fake save_note that records each call."""
    saved = []
    monkeypatch.setitem(agent.TOOLS, "save_note", {
        "function": lambda title, content: saved.append(title) or {"saved": True, "id": 1, "title": title},
        "requires_confirmation": True,
        "schema": {"type": "function", "function": {"name": "save_note"}},
    })
    monkeypatch.setattr(agent, "PENDING_ACTIONS", {
        "abc123": {"tool": "save_note", "arguments": {"title": "Nimbus", "content": "$8/month"}},
    })
    return saved


def test_confirm_runs_the_pending_action(pending_note):
    response = app.test_client().post("/api/actions/abc123/confirm")

    assert response.status_code == 200
    assert response.get_json() == {"status": "confirmed", "result": {"saved": True, "id": 1, "title": "Nimbus"}}
    assert pending_note == ["Nimbus"]


def test_confirm_works_only_once(pending_note):
    client = app.test_client()
    client.post("/api/actions/abc123/confirm")

    second = client.post("/api/actions/abc123/confirm")

    assert second.status_code == 404
    assert pending_note == ["Nimbus"]  # saved once, not twice


def test_cancel_discards_without_running(pending_note):
    client = app.test_client()

    cancelled = client.post("/api/actions/abc123/cancel")
    confirm_after = client.post("/api/actions/abc123/confirm")

    assert cancelled.status_code == 200
    assert cancelled.get_json() == {"status": "cancelled"}
    assert confirm_after.status_code == 404
    assert pending_note == []


def test_unknown_action_id_is_rejected(pending_note):
    client = app.test_client()

    assert client.post("/api/actions/made-up/confirm").status_code == 404
    assert client.post("/api/actions/made-up/cancel").status_code == 404
    assert pending_note == []
