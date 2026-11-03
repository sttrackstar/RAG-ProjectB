import pytest

import app as app_module
import db
from tests.helpers import signed_up_client


@pytest.fixture(autouse=True)
def temp_observability_log(tmp_path, monkeypatch):
    """Send every test's observability log to a temporary file, never the real one."""
    path = tmp_path / "runs.jsonl"
    monkeypatch.setenv("OBSERVABILITY_LOG", str(path))
    return path


@pytest.fixture(autouse=True)
def temp_database(tmp_path, monkeypatch):
    """Give every test a fresh, empty database, never the real one."""
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setattr(app_module, "ACTION_OWNERS", {})
    db.init_db()


@pytest.fixture
def client():
    """A test client that is signed up and logged in."""
    return signed_up_client()
