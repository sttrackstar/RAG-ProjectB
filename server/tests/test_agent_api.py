from unittest.mock import patch

from app import app


def test_agent_endpoint_returns_answer():
    fake_result = {
        "answer": "Nimbus Pro costs $8 per month.",
        "steps": [],
    }

    with patch("app.run_agent", return_value=fake_result) as mock_agent:
        client = app.test_client()

        response = client.post(
            "/api/agent",
            json={"question": "How much does Nimbus Pro cost?"},
        )

    assert response.status_code == 200
    assert response.get_json() == fake_result
    mock_agent.assert_called_once_with("How much does Nimbus Pro cost?")


def test_agent_endpoint_rejects_missing_question():
    client = app.test_client()

    response = client.post("/api/agent", json={})

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "Question is required"
    }


def test_agent_endpoint_rejects_empty_question():
    client = app.test_client()

    response = client.post(
        "/api/agent",
        json={"question": "   "}
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "Question is required"
    }


def test_warmup_endpoint_starts_warm_up_in_background():
    with patch("app.threading.Thread") as mock_thread:
        client = app.test_client()

        response = client.post("/api/warmup")

    assert response.status_code == 202
    mock_thread.assert_called_once()
    assert mock_thread.call_args.kwargs["target"].__name__ == "warm_up"
    mock_thread.return_value.start.assert_called_once()