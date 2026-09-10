"""
Dr. Sumaiya Mohammad - Personal Chatbot (runs on localhost).

Quick start:
  1. python -m pip install -r requirements.txt
  2. python app.py
  3. Open http://localhost:5000 in your browser

Convenience launcher for the web app:
"""

from app import app

if __name__ == "__main__":
    print("=" * 60)
    print(" Personal Chatbot for Dr. Sumaiya Mohammad")
    print(" Open your browser at:  http://localhost:5000")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=False)
