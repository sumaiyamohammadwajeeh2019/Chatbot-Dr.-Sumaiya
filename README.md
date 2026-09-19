# Crew Agent AI – Personal Assistant Chatbot (Fresh Rebuild)

A personal AI chatbot skeleton built with **Flask** and a **CrewAI agent crew**
(one Agent → one Task → sequential Process) that runs **entirely on your own
computer** — no API key, no internet connection needed.

> **The knowledge base was wiped for a fresh rebuild.** The chatbot engine is
> fully working, but it currently has no profile data. Fill in `BIO_DATA` and
> `KNOWLEDGE` in `chatbot.py` (see "Adding your data" below) and the bot will
> answer the new information right away.

## No API key needed

There is no API key, no `.env` file, no Groq/OpenAI account and no internet
connection involved. Install the packages, start the server and chat — the bot
works offline and is free to run.

## Features

- Web chat interface (HTML + CSS + vanilla JS, no build step)
- Conversation memory while the server is running
- Quick-question buttons and a "New chat" reset button
- Friendly answers for questions it cannot answer (it never invents facts)
- Runs on `localhost:5000` and is reachable from other devices on your Wi-Fi

## How the "Crew Agent AI" works

| Part | File | Job |
|------|------|-----|
| `BIO_DATA` / `PROFILE` | `chatbot.py` | Structured profile store (currently empty) |
| `KNOWLEDGE` | `chatbot.py` | Topic entries that turn a question into an answer |
| `LocalAgentBrain` | `chatbot.py` | Matches your question to a topic and writes the reply |
| `LocalCrewLLM` | `chatbot.py` | The language model CrewAI drives — answered locally |
| `build_crew()` | `chatbot.py` | Builds the CrewAI Agent, Task and Crew |
| `ChatSession` | `chatbot.py` | Keeps the conversation history |
| `app.py` | `app.py` | Flask server with `/`, `/chat`, `/reset`, `/health` |

## Requirements

- Python 3.10 or newer
- No API key, no account, no credit card
- Optional: `crewai` + `langchain-core` — answers come from the same local
  brain with or without it (skipping them keeps the Render free-plan build
  fast and inside its 512 MB memory limit)

## Setup

1. **Copy or clone the project** onto the machine where you want to run it.

2. **Create a virtual environment** (recommended):

   ```bash
   python -m venv .venv
   ```

   Activate it:

   - Windows:  `.venv\Scripts\activate`
   - macOS/Linux:  `source .venv/bin/activate`

3. **Install dependencies**:

   ```bash
   python -m pip install -r requirements.txt
   ```

   Optional (to run the full CrewAI crew locally):

   ```bash
   python -m pip install "crewai==0.11.2" "langchain-core>=0.1.42,<0.2"
   ```

   The replies are identical either way — every answer is written by the local
   brain in `chatbot.py`.

4. **Run**:

   ```bash
   python app.py
   ```

   Then open <http://localhost:5000> in your browser. Check
   <http://localhost:5000/health> to confirm the server is alive. To stop the
   server, press **CTRL+C**.

## Adding your data (rebuild guide)

All the bot knows lives in **`chatbot.py`**. Three places, one job each:

1. **`BIO_DATA`** — the facts. Add keys/values to the empty sections
   (`personal`, `other`, `service`, `education`, `career_history`):

   ```python
   "personal": {
       "father_name": "…",
       "date_of_birth": "…",
       "mobile_no": "…",
   },
   ```

   Anything you add here is automatically rendered into the agent's profile
   (`PROFILE`) and appears in the "show me all information" answer.

2. **`KNOWLEDGE`** — the answers. Add one `Topic` per subject:

   ```python
   Topic(
       "designation",
       ("designation", "position", "job title"),   # words users will type
       "She is an Assistant Professor …",          # the answer shown
   ),
   ```

3. **`OVERVIEW_ANSWER`** — the "tell me about …" summary. Rewrite it once the
   profile is filled in.

4. **`PERSON_NAME`** — replace the placeholder `"the Profile Owner"` with the
   real name (it appears in the web UI and the replies), and update the
   subtitle line in `templates/index.html` if you want.

Then run `python test_chatbot.py` and the checks confirm the new data works.

## Deploying on Render

The repo ships with a **Blueprint** (`render.yaml`): free Python web service,
`pip install -r requirements.txt` as the build command and
`gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120`
as the start command, with a health check at `/health`.

**New +** then **Blueprint**, pick this repository, and Render reads
`render.yaml` and creates the service.

> Free instances sleep after about 15 minutes without traffic and take roughly
> a minute to wake again on the next request.

> The Render build installs only Flask and Gunicorn. The optional CrewAI
> packages are skipped there, so the build finishes quickly and the service
> boots comfortably inside the free plan's 512 MB memory limit.

> **If pushes are not deployed:** check the service's **Events** tab and use
> **Manual Deploy → Deploy latest commit**; also confirm **Settings →
> Auto-Deploy** is on for the `main` branch.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Address already in use` | Another program is using port 5000. Stop it, or run with another port: `set PORT=5001` then `python app.py` |
| Browser shows "can't reach this page" | Make sure the terminal still shows the server running, then reload <http://localhost:5000> |
| `ModuleNotFoundError: crewai` | Optional package: the app works without it. To run the CrewAI crew locally: `python -m pip install "crewai==0.11.2" "langchain-core>=0.1.42,<0.2"` |
| A pydantic warning about V1/V2 models on start-up | Harmless: comes from CrewAI's own LangChain integration and is filtered out by `chatbot.py` |
| The bot answers "I don't have that information yet" | That is correct for the empty rebuild — add the fact to `BIO_DATA` and a `Topic` to `KNOWLEDGE` |

## Privacy

- No API key or secret is stored anywhere in this project.
- Nothing is sent to the internet: the answers are generated locally
  (CrewAI telemetry is disabled).
- Conversations live only in memory and disappear when the server stops.
