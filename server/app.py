import threading
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request

import agent
from agent import cancel_action, confirm_action, run_agent
from llm import warm_up
from observability import get_run, list_runs

# Load settings from the .env file in the repo root(one folder up from server)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def create_app():
    app = Flask(__name__)

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"})

    @app.route("/api/agent", methods=["POST"])
    def ask_agent():
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return jsonify({"error": "A JSON object is required"}), 400

        question = data.get("question")

        if not isinstance(question, str) or not question.strip():
            return jsonify({"error": "Question is required"}), 400

        result = run_agent(question.strip())

        return jsonify(result), 200

    @app.route("/api/warmup", methods=["POST"])
    def warmup():
        # Load the model in the background and reply right away, so the
        # browser never waits for it.
        threading.Thread(target=warm_up, daemon=True).start()
        return jsonify({"status": "warming up"}), 202

    @app.route("/api/runs", methods=["GET"])
    def recent_runs():
        limit = request.args.get("limit", default=20, type=int)
        return jsonify(list_runs(limit=max(1, min(limit, 100))))

    @app.route("/api/runs/<run_id>", methods=["GET"])
    def run_log(run_id):
        events = get_run(run_id)
        if not events:
            return jsonify({"error": "No run with that id"}), 404
        return jsonify({"run_id": run_id, "events": events})

    # Confirmation guardrail: a consequential action (like save_note) only runs
    # when the user approves the pending action the agent paused on.
    @app.route("/api/actions/<action_id>/confirm", methods=["POST"])
    def confirm(action_id):
        if action_id not in agent.PENDING_ACTIONS:
            return jsonify({"error": "No pending action with that id. It may have already run or been cancelled."}), 404
        return jsonify({"status": "confirmed", "result": confirm_action(action_id)}), 200

    @app.route("/api/actions/<action_id>/cancel", methods=["POST"])
    def cancel(action_id):
        if action_id not in agent.PENDING_ACTIONS:
            return jsonify({"error": "No pending action with that id."}), 404
        cancel_action(action_id)
        return jsonify({"status": "cancelled"}), 200

    return app


app = create_app()