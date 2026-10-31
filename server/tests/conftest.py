import pytest


@pytest.fixture(autouse=True)
def temp_observability_log(tmp_path, monkeypatch):
    """Send every test's observability log to a temporary file, never the real one."""
    path = tmp_path / "runs.jsonl"
    monkeypatch.setenv("OBSERVABILITY_LOG", str(path))
    return path
