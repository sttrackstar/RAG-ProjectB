import agent
import app as app_module
import db
from app import app
from tests.helpers import signed_up_client

FINAL = {"type": "final", "content": "Hi", "message": {"role": "assistant", "content": "Hi"}}


def test_signup_logs_you_in_and_stores_a_hashed_password(client):
    me = client.get("/api/me")

    assert me.status_code == 200
    assert me.get_json() == {"id": 1, "username": "tester"}
    with app.app_context():
        row = db.get_db().execute("SELECT password_hash FROM users WHERE username = 'tester'").fetchone()
    assert row["password_hash"] != "password123"
    assert "password123" not in row["password_hash"]


def test_signup_validates_input():
    new = app.test_client()

    assert new.post("/api/signup", json={"username": "ab", "password": "password123"}).status_code == 400
    assert new.post("/api/signup", json={"username": "valid_name", "password": "short"}).status_code == 400
    assert new.post("/api/signup", json={"username": "bad name!", "password": "password123"}).status_code == 400
    assert new.post("/api/signup", data="not json").status_code == 400


def test_duplicate_username_is_rejected(client):
    again = app.test_client().post("/api/signup", json={"username": "TESTER", "password": "password123"})

    assert again.status_code == 409


def test_login_and_logout():
    signed_up_client()
    new = app.test_client()

    wrong = new.post("/api/login", json={"username": "tester", "password": "wrong-password"})
    unknown = new.post("/api/login", json={"username": "nobody", "password": "password123"})
    right = new.post("/api/login", json={"username": "tester", "password": "password123"})

    assert wrong.status_code == 401
    assert unknown.get_json() == wrong.get_json()  # same message: don't reveal which part was wrong
    assert right.status_code == 200
    assert new.get("/api/me").status_code == 200

    new.post("/api/logout")

    assert new.get("/api/me").status_code == 401


def test_agent_and_history_require_login():
    anonymous = app.test_client()

    assert anonymous.post("/api/agent", json={"question": "hello"}).status_code == 401
    assert anonymous.get("/api/conversations").status_code == 401
    assert anonymous.get("/api/runs").status_code == 401


def test_conversations_are_saved_and_private(monkeypatch, client):
    monkeypatch.setattr(agent, "generate", lambda messages, tools: FINAL)
    other = signed_up_client("other_user", "password456")

    client.post("/api/agent", json={"question": "my question"})
    other.post("/api/agent", json={"question": "their question"})

    mine = client.get("/api/conversations").get_json()
    theirs = other.get("/api/conversations").get_json()

    assert [c["question"] for c in mine] == ["my question"]
    assert [c["question"] for c in theirs] == ["their question"]
    assert mine[0]["answer"] == "Hi"
    assert mine[0]["steps"] == []
    assert mine[0]["run_id"]


def test_pending_confirmations_are_not_saved_to_history(monkeypatch, client):
    pending = {"answer": "Please confirm.", "steps": [], "run_id": "r1", "duration_ms": 5,
               "pending_action": {"id": "abc123", "tool": "save_note", "arguments": {}}}
    monkeypatch.setattr(app_module, "run_agent", lambda goal, user_id=None: dict(pending))

    response = client.post("/api/agent", json={"question": "Save a note"})

    assert response.get_json()["pending_action"]["id"] == "abc123"
    assert "conversation_id" not in response.get_json()
    assert client.get("/api/conversations").get_json() == []
    assert app_module.ACTION_OWNERS["abc123"] == 1


def test_run_logs_are_private(monkeypatch, client):
    monkeypatch.setattr(agent, "generate", lambda messages, tools: FINAL)
    run_id = client.post("/api/agent", json={"question": "mine"}).get_json()["run_id"]
    other = signed_up_client("other_user", "password456")

    assert client.get(f"/api/runs/{run_id}").status_code == 200
    assert other.get(f"/api/runs/{run_id}").status_code == 404
    assert other.get("/api/runs").get_json() == []


def test_conversations_survive_a_restart(monkeypatch, client):
    monkeypatch.setattr(agent, "generate", lambda messages, tools: FINAL)
    client.post("/api/agent", json={"question": "remember me"})

    restarted = __import__("app").create_app()  # a fresh app on the same database file
    later = restarted.test_client()
    later.post("/api/login", json={"username": "tester", "password": "password123"})

    assert [c["question"] for c in later.get("/api/conversations").get_json()] == ["remember me"]
