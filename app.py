"""
Personal chatbot for Dr. Sumaiya Mohammad - web app (runs on localhost).

Run with:  python app.py
Then open: http://localhost:5000
"""

import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from chatbot import ChatSession

load_dotenv()

app = Flask(__name__)

# One shared session; gives the bot conversation memory while the server runs.
session = ChatSession()


@app.route("/")
def index():
    """Serve the chat interface."""
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    """Handle one chat message. Expects JSON: {"message": "..."}."""
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"error": "Message cannot be empty."}), 400

    try:
        reply = session.send(message)
        return jsonify({"reply": reply})
    except Exception as exc:  # surface API / network errors to the UI
        return jsonify({"error": str(exc)}), 500


@app.route("/reset", methods=["POST"])
def reset():
    """Clear the conversation history."""
    session.reset()
    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    print("=" * 60)
    print(" Personal Chatbot for Dr. Sumaiya Mohammad")
    print(" On this PC :  http://localhost:{0}".format(port))
    print(" On your LAN:  http://<this-computer-ip>:{0}".format(port))
    print(" Press CTRL+C in this terminal to stop the server.")
    print("=" * 60)
    # 0.0.0.0 = reachable from this PC AND other devices on your network.
    app.run(host="0.0.0.0", port=port, debug=False)