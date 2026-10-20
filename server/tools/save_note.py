import json
import os
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_NOTES_FILE = Path(__file__).resolve().parent.parent / "data" / "notes.json"
MAX_TITLE_LENGTH = 200
MAX_CONTENT_LENGTH = 5000


def save_note(title: str, content: str) -> dict:
    """Save a research note to the local notes file.

    Returns {"saved": True, "id": int, "title": str} on success,
    or {"error": str} if the note is invalid or can't be written.
    """
    if not isinstance(title, str) or not title.strip():
        return {"error": "title must be a non-empty string"}
    if not isinstance(content, str) or not content.strip():
        return {"error": "content must be a non-empty string"}
    if len(title) > MAX_TITLE_LENGTH or len(content) > MAX_CONTENT_LENGTH:
        return {"error": f"title must be under {MAX_TITLE_LENGTH} and content under {MAX_CONTENT_LENGTH} characters"}

    notes_file = Path(os.environ.get("NOTES_FILE", DEFAULT_NOTES_FILE))

    try:
        notes = json.loads(notes_file.read_text(encoding="utf-8")) if notes_file.exists() else []
    except (OSError, ValueError):
        return {"error": "Could not read the notes file"}

    note = {
        "id": len(notes) + 1,
        "title": title.strip(),
        "content": content.strip(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    notes.append(note)

    try:
        notes_file.parent.mkdir(parents=True, exist_ok=True)
        notes_file.write_text(json.dumps(notes, indent=2), encoding="utf-8")
    except OSError:
        return {"error": "Could not write the notes file"}

    return {"saved": True, "id": note["id"], "title": note["title"]}
