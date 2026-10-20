import json

import pytest

from tools.registry import TOOLS
from tools.save_note import save_note


@pytest.fixture
def notes_file(tmp_path, monkeypatch):
    """Point save_note at a temporary file so tests never touch real notes."""
    path = tmp_path / "notes.json"
    monkeypatch.setenv("NOTES_FILE", str(path))
    return path


def test_saves_note_to_file(notes_file):
    result = save_note("Nimbus Pro price", "  $8 per month (nimbus-faq.txt)  ")

    assert result == {"saved": True, "id": 1, "title": "Nimbus Pro price"}
    notes = json.loads(notes_file.read_text(encoding="utf-8"))
    assert len(notes) == 1
    assert notes[0]["content"] == "$8 per month (nimbus-faq.txt)"  # whitespace stripped
    assert "created_at" in notes[0]


def test_appends_to_existing_notes(notes_file):
    save_note("First", "one")
    result = save_note("Second", "two")

    assert result["id"] == 2
    assert [n["title"] for n in json.loads(notes_file.read_text(encoding="utf-8"))] == ["First", "Second"]


@pytest.mark.parametrize("title, content", [
    ("", "content"),
    ("   ", "content"),
    ("Title", ""),
    (42, "content"),
    ("Title", None),
])
def test_rejects_missing_or_non_string_fields(notes_file, title, content):
    assert "error" in save_note(title, content)
    assert not notes_file.exists()


def test_rejects_overly_long_content(notes_file):
    assert "error" in save_note("Title", "x" * 5001)
    assert not notes_file.exists()


def test_corrupted_notes_file_returns_error(notes_file):
    notes_file.write_text("this is not json", encoding="utf-8")

    assert save_note("Title", "content") == {"error": "Could not read the notes file"}


def test_save_note_requires_confirmation():
    assert TOOLS["save_note"]["function"] is save_note
    assert TOOLS["save_note"]["requires_confirmation"] is True
