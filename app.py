"""
Crew Agent AI - web app for the personal assistant chatbot of
Dr. Sumaiya Mohammad.

Runs 100% on this computer: no API key, no .env file and no internet
connection are needed.

Run with:  python app.py
Then open: http://localhost:5000
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Optional

from flask import Flask, jsonify, render_template, request

from chatbot import AGENT_NAME, CREW_AVAILABLE, PERSON_NAME, ChatSession

# Build stamp: bump this value whenever the knowledge base or app changes.
# /health reports it, so you can always verify which build is live on Render.
APP_BUILD = "2026-09-19.3"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
LOGGER = logging.getLogger("crew-agent-ai")

# The chat box in the browser allows 1000 characters; keep a little head room.
MAX_MESSAGE_LENGTH = 2000

app = Flask(__name__)
app.json.sort_keys = False

# One shared session, so the bot remembers the conversation while the server
# runs. Created on first use (thread-safe) so the web UI always loads.
_session: Optional[ChatSession] = None
_session_lock = threading.Lock()


def get_session() -> ChatSession:
    """Return the single shared ChatSession, creating it on first use."""
    global _session
    if _session is None:
        with _session_lock:
            if _session is None:
                _session = ChatSession()
    return _session


def _clean_message(raw: object) -> str:
    """Turn whatever the client sent into a trimmed, length-checked message."""
    message = str(raw or "").strip()
    if len(message) > MAX_MESSAGE_LENGTH:
        message = message[:MAX_MESSAGE_LENGTH]
    return message


@app.route("/")
def index():
    """Serve the chat interface."""
    return render_template(
        "index.html", agent_name=AGENT_NAME, person_name=PERSON_NAME
    )


@app.route("/chat", methods=["POST"])
def chat():
    """Answer one chat message. Expects JSON: {"message": "..."}."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):  # no body, bad JSON or a JSON array
        data = {}
    message = _clean_message(data.get("message"))
    if not message:
        return jsonify({"error": "Please type a message first."}), 400

    try:
        reply = get_session().send(message)
    except ValueError as exc:  # empty / unusable input
        return jsonify({"error": str(exc)}), 400
    except Exception:  # never break the chat window
        LOGGER.exception("Could not produce a reply for: %r", message)
        return (
            jsonify(
                {
                    "error": "Sorry, something went wrong while answering. "
                    "Please try again."
                }
            ),
            500,
        )

    return jsonify({"reply": reply})


@app.route("/reset", methods=["POST"])
def reset():
    """Clear the conversation history."""
    if _session is not None:
        _session.reset()
    return jsonify({"ok": True})


@app.route("/health")
def health():
    """Small status page: handy to check that the server is alive."""
    return jsonify(
        {
            "status": "ok",
            "agent": AGENT_NAME,
            "person": PERSON_NAME,
            "engine": (
                "CrewAI agent (local, no API key)"
                if CREW_AVAILABLE
                else "Local brain (CrewAI optional package not installed)"
            ),
            "build": APP_BUILD,
        }
    )


@app.route("/favicon.ico")
def favicon():
    """The page embeds its icon inline, so no icon file is needed."""
    return "", 204


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    print("=" * 60)
    print(" Crew Agent AI - Personal Chatbot for Dr. Sumaiya Mohammad")
    print(" No API key needed: everything runs on this computer.")
    print(" On this PC :  http://localhost:{0}".format(port))
    print(" On your LAN:  http://<this-computer-ip>:{0}".format(port))
    print(" Press CTRL+C in this terminal to stop the server.")
    print("=" * 60)
    # 0.0.0.0 = reachable from this PC AND other devices on your network.
    app.run(host="0.0.0.0", port=port, debug=False)