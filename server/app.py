from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request

from agent import run_agent

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

    return app


app = create_app()