# Dr. Sumaiya Mohammad – Personal Assistant Chatbot

A personal AI chatbot that answers questions about **Dr. Sumaiya Mohammad** —
Assistant Professor, Department of Physiology, Shaheed Syed Nazrul Islam
Medical College (SSNIMC), Kishoreganj.

The bot runs as a small **Flask** web app, speaks to the **Groq API**
(inference engine) using the LLM model `openai/gpt-oss-20b`, and remembers the
conversation while the server is running.

---

## Features

- Web chat interface (HTML + CSS + vanilla JS, no front-end build step)
- Conversation memory within a single server session
- "New chat" button to reset the conversation
- Friendly error handling when the Groq API key is missing or the network fails
- Runs on `localhost:5000` and is reachable from other devices on your LAN

---

## Project structure

```
chatbot/
├── app.py               # Flask web server (routes: /, /chat, /reset)
├── main.py              # Convenience launcher (same as python app.py)
├── chatbot.py           # Bot core: system prompt + ChatSession (Groq API)
├── requirements.txt     # Python dependencies
├── templates/index.html # Chat interface
├── static/style.css     # Chat styling
├── .env.example         # Template for the environment variables (safe to commit)
└── .env                 # YOUR REAL SECRETS — do not commit this file
```

---

## Requirements

- Python 3.10+ (the code uses `str | None` type hints)
- A free **Groq API key** from <https://console.groq.com>

---

## Setup

1. **Clone or copy the project** onto the machine where you want to run it.

2. **Create a virtual environment** (recommended):

   ```bash
   python -m venv .venv
   ```

   Then activate it:

   - Windows:  `.venv\Scripts\activate`
   - macOS/Linux:  `source .venv/bin/activate`

3. **Install dependencies**:

   ```bash
   python -m pip install -r requirements.txt
   ```

4. **Create your `.env` file** — copy the template and add your own key:

   ```bash
   cp .env.example .env      # Windows:  copy .env.example .env
   ```

   Then edit `.env` so `GROQ_API_KEY=your_real_groq_api_key`.

   | Variable       | Meaning                                | Example                 |
   |----------------|----------------------------------------|-------------------------|
   | `GROQ_API_KEY` | Your Groq API key (required)           | `gsk_...`               |
   | `MODEL`        | Groq model to use                      | `openai/gpt-oss-20b`    |
   | `PORT`         | Port the Flask server listens on       | `5000`                  |

---

## Run

```bash
python app.py
```

Then open <http://localhost:5000> in your browser.

To stop the server, press **CTRL+C** in the terminal.

> Tip: the server binds to `0.0.0.0`, so devices on the same Wi-Fi/LAN can
> reach it at `http://<this-computer-ip>:5000`.

---

## Security notes

- **Never commit your real `.env` file.** It contains your private API key.
  This project already ships a `.gitignore` that excludes `.env`.
- If your key is ever exposed (e.g. pushed to a public repo), **revoke it
  immediately** in the Groq console and generate a new one.

---

## About Dr. Sumaiya Mohammad

- Designation: Assistant Professor
- Department: Department of Physiology
- Institution: Shaheed Syed Nazrul Islam Medical College, Kishoreganj
- Working at the institution since: 2023
- School: Monipur High School
- College: Viqarunnisa Noon College

### Working experience & responsibilities

- Hostel Superintendent of Shila Islam Ladies Hostel, Shaheed Syed Nazrul Islam
  Medical College, Kishoreganj
- Member of the Hostel Disciplinary Committee, SSNIMC
- Member of the Antiragging Committee, SSNIMC
- Member of the Pair Medical College Visiting Committee, SSNIMC
- Member of the Medical Education Unit, SSNIMC
- Vice President of the Mymensingh region, Bangladesh Society of Physiologists
- Member of the Education Sub-committee, Operational Manual Reform Sub-committee
  and Teachers Benefit Sub-committee of the Bangladesh Society of Physiologists