from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify

# Load settings from the .env file in the repo root(one folder up from server)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def create_app():
    app = Flask(__name__)

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"})

    return app


app = create_app()