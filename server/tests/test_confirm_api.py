import pytest

import agent
import app as app_module
from tests.helpers import signed_up_client


@pytest.fixture
def pending_note(monkeypatch, client):
    """A pending save_note action owned by the logged-in user (id 1), with a fake save_note."""
    saved = []
    monkeypatch.setitem(agent.TOOLS, "save_note", {
        "function": lambda title, content: saved.append(title) or {"saved": True, "id": 1, "title": title},
        "requires_confirmation": True,
        "schema": {"type": "function", "function": {"name": "save_note"}},
    })
    monkeypatch.setattr(agent, "PENDING_ACTIONS", {
        "abc123": {"tool": "save_note", "arguments": {"title": "Nimbus", "content": "$8/month"}},
    })
    monkeypatch.setattr(app_module, "ACTION_OWNERS", {"abc123": 1})
    return saved


def test_confirm_runs_the_pending_action(pending_note, client):
    response = client.post("/api/actions/abc123/confirm")

    assert response.status_code == 200
    assert response.get_json() == {"status": "confirmed", "result": {"saved": True, "id": 1, "title": "Nimbus"}}
    assert pending_note == ["Nimbus"]


def test_confirm_works_only_once(pending_note, client):
    client.post("/api/actions/abc123/confirm")

    second = client.post("/api/actions/abc123/confirm")

    assert second.status_code == 404
    assert pending_note == ["Nimbus"]  # saved once, not twice


def test_cancel_discards_without_running(pending_note, client):
    cancelled = client.post("/api/actions/abc123/cancel")
    confirm_after = client.post("/api/actions/abc123/confirm")

    assert cancelled.status_code == 200
    assert cancelled.get_json() == {"status": "cancelled"}
    assert confirm_after.status_code == 404
    assert pending_note == []


def test_unknown_action_id_is_rejected(pending_note, client):
    assert client.post("/api/actions/made-up/confirm").status_code == 404
    assert client.post("/api/actions/made-up/cancel").status_code == 404
    assert pending_note == []


def test_another_user_cannot_confirm_or_cancel(pending_note):
    stranger = signed_up_client("stranger", "password456")

    assert stranger.post("/api/actions/abc123/confirm").status_code == 404
    assert stranger.post("/api/actions/abc123/cancel").status_code == 404
    assert pending_note == []
    assert "abc123" in agent.PENDING_ACTIONS  # still waiting for its owner
