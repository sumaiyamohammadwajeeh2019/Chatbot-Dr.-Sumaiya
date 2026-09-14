"""Crew Agent AI - Personal Chatbot for Dr. Sumaiya Mohammad.

Runs on localhost with no API key and no internet connection.

Quick start:
  1. python -m pip install -r requirements.txt
  2. python app.py
  3. Open http://localhost:5000 in your browser

Convenience launcher for the web app:
"""

import os

from app import app

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    print("=" * 60)
    print(" Crew Agent AI - Personal Chatbot for Dr. Sumaiya Mohammad")
    print(" No API key needed: everything runs on this computer.")
    print(" Open your browser at:  http://localhost:{0}".format(port))
    print("=" * 60)
    app.run(host="0.0.0.0", port=port, debug=False)
