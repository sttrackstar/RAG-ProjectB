"""SQLite database: users and their saved conversations.

Uses Python's built-in sqlite3. The file comes from DATABASE_URL
(e.g. sqlite:///data/app.db, relative to server/); it's git-ignored.
"""
import json
import os
import sqlite3
from pathlib import Path

from flask import g

SERVER_DIR = Path(__file__).resolve().parent
DEFAULT_DB = SERVER_DIR / "data" / "app.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    question TEXT NOT NULL,
    answer TEXT,
    steps_json TEXT NOT NULL DEFAULT '[]',
    run_id TEXT,
    duration_ms INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id, id);
"""


def database_path() -> Path:
    url = os.environ.get("DATABASE_URL", "")
    if url.startswith("sqlite:///"):
        path = Path(url[len("sqlite:///"):])
        return path if path.is_absolute() else SERVER_DIR / path
    return DEFAULT_DB


def connect() -> sqlite3.Connection:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db() -> None:
    with connect() as connection:
        connection.executescript(SCHEMA)


def get_db() -> sqlite3.Connection:
    """One connection per request, closed by close_db."""
    if "db" not in g:
        g.db = connect()
    return g.db


def close_db(_error=None) -> None:
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def save_conversation(user_id: int, question: str, result: dict) -> int:
    db = get_db()
    cursor = db.execute(
        "INSERT INTO conversations (user_id, question, answer, steps_json, run_id, duration_ms) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, question, result.get("answer"), json.dumps(result.get("steps", [])),
         result.get("run_id"), result.get("duration_ms")),
    )
    db.commit()
    return cursor.lastrowid


def list_conversations(user_id: int, limit: int = 20) -> list:
    rows = get_db().execute(
        "SELECT id, question, answer, steps_json, run_id, duration_ms, created_at "
        "FROM conversations WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    return [
        {**{key: row[key] for key in row.keys() if key != "steps_json"}, "steps": json.loads(row["steps_json"])}
        for row in rows
    ]

def delete_conversation(user_id: int, conversation_id: int) -> bool:
    db = get_db()

    cursor = db.execute(
        "DELETE FROM conversations WHERE id = ? AND user_id = ?",
        (conversation_id, user_id),
    )

    db.commit()

    return cursor.rowcount > 0
