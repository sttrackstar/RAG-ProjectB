"""Sign up, log in and log out, with hashed passwords and Flask sessions."""
import functools
import re
import sqlite3

from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from db import get_db

bp = Blueprint("auth", __name__, url_prefix="/api")

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,30}$")
MIN_PASSWORD_LENGTH = 8


def current_user_id():
    return session.get("user_id")


def login_required(view):
    """Reject the request with 401 unless someone is logged in."""
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if current_user_id() is None:
            return jsonify({"error": "Please log in first."}), 401
        return view(*args, **kwargs)
    return wrapped


def _credentials():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None, None
    username, password = data.get("username"), data.get("password")
    if not isinstance(username, str) or not isinstance(password, str):
        return None, None
    return username.strip(), password


@bp.route("/signup", methods=["POST"])
def signup():
    username, password = _credentials()
    errors = []
    if not username or not USERNAME_PATTERN.match(username):
        errors.append("Username must be 3-30 letters, numbers or underscores.")
    if not password or len(password) < MIN_PASSWORD_LENGTH:
        errors.append(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if errors:
        return jsonify({"errors": errors}), 400

    db = get_db()
    try:
        cursor = db.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, generate_password_hash(password)),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({"errors": ["That username is taken."]}), 409

    session.clear()
    session["user_id"] = cursor.lastrowid
    return jsonify({"id": cursor.lastrowid, "username": username}), 201


@bp.route("/login", methods=["POST"])
def login():
    username, password = _credentials()
    user = None
    if username and password:
        user = get_db().execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?", (username,)
        ).fetchone()
    # Same message whether the username or the password was wrong.
    if user is None or not check_password_hash(user["password_hash"], password):
        return jsonify({"errors": ["Incorrect username or password."]}), 401

    session.clear()
    session["user_id"] = user["id"]
    return jsonify({"id": user["id"], "username": user["username"]}), 200


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"status": "logged out"}), 200


@bp.route("/me", methods=["GET"])
def me():
    user_id = current_user_id()
    user = None
    if user_id is not None:
        user = get_db().execute("SELECT id, username FROM users WHERE id = ?", (user_id,)).fetchone()
    if user is None:
        session.clear()
        return jsonify({"error": "Not logged in."}), 401
    return jsonify({"id": user["id"], "username": user["username"]}), 200
