import os
import secrets
import threading
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request

import agent
from agent import cancel_action, confirm_action, run_agent
from auth import bp as auth_bp
from auth import current_user_id, login_required
from db import close_db, init_db, list_conversations, save_conversation
from llm import warm_up
from observability import get_run, list_runs

# Load settings from the .env file in the repo root(one folder up from server)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Who each pending action belongs to, so only that user can confirm or cancel it.
ACTION_OWNERS = {}


def create_app():
    app = Flask(__name__)
    # Signs the session cookie. Without SECRET_KEY in .env, sessions reset on restart.
    app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")

    init_db()
    app.teardown_appcontext(close_db)
    app.register_blueprint(auth_bp)

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"})

    @app.route("/api/agent", methods=["POST"])
    @login_required
    def ask_agent():
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return jsonify({"error": "A JSON object is required"}), 400

        question = data.get("question")

        if not isinstance(question, str) or not question.strip():
            return jsonify({"error": "Question is required"}), 400

        user_id = current_user_id()
        result = run_agent(question.strip(), user_id=user_id)
        if result.get("pending_action"):
            # Not saved to history: the action can't be confirmed from a reopened conversation.
            ACTION_OWNERS[result["pending_action"]["id"]] = user_id
        else:
            result["conversation_id"] = save_conversation(user_id, question.strip(), result)

        return jsonify(result), 200

    @app.route("/api/conversations", methods=["GET"])
    @login_required
    def conversations():
        limit = request.args.get("limit", default=20, type=int)
        return jsonify(list_conversations(current_user_id(), limit=max(1, min(limit, 100))))

    @app.route("/api/warmup", methods=["POST"])
    def warmup():
        # Load the model in the background and reply right away, so the
        # browser never waits for it.
        threading.Thread(target=warm_up, daemon=True).start()
        return jsonify({"status": "warming up"}), 202

    @app.route("/api/runs", methods=["GET"])
    @login_required
    def recent_runs():
        limit = request.args.get("limit", default=20, type=int)
        return jsonify(list_runs(limit=max(1, min(limit, 100)), user_id=current_user_id()))

    @app.route("/api/runs/<run_id>", methods=["GET"])
    @login_required
    def run_log(run_id):
        events = get_run(run_id, user_id=current_user_id())
        if not events:
            return jsonify({"error": "No run with that id"}), 404
        return jsonify({"run_id": run_id, "events": events})

    # Confirmation guardrail: a consequential action (like save_note) only runs
    # when the user who asked approves the pending action the agent paused on.
    def _owns_pending(action_id):
        return action_id in agent.PENDING_ACTIONS and ACTION_OWNERS.get(action_id) == current_user_id()

    @app.route("/api/actions/<action_id>/confirm", methods=["POST"])
    @login_required
    def confirm(action_id):
        if not _owns_pending(action_id):
            return jsonify({"error": "No pending action with that id. It may have already run or been cancelled."}), 404
        ACTION_OWNERS.pop(action_id, None)
        return jsonify({"status": "confirmed", "result": confirm_action(action_id)}), 200

    @app.route("/api/actions/<action_id>/cancel", methods=["POST"])
    @login_required
    def cancel(action_id):
        if not _owns_pending(action_id):
            return jsonify({"error": "No pending action with that id."}), 404
        ACTION_OWNERS.pop(action_id, None)
        cancel_action(action_id)
        return jsonify({"status": "cancelled"}), 200

    return app


app = create_app()
