import app as app_module


def signed_up_client(username="tester", password="password123"):
    """A test client with a new account, logged in."""
    client = app_module.app.test_client()
    response = client.post("/api/signup", json={"username": username, "password": password})
    assert response.status_code == 201, response.get_json()
    return client
