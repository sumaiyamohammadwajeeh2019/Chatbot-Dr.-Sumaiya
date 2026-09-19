# Crew Agent AI – Personal Assistant Chatbot for Dr. Sumaiya Mohammad

A personal AI chatbot that answers questions about **Dr. Sumaiya Mohammad** —
Assistant Professor, Department of Physiology, Shaheed Syed Nazrul Islam
Medical College (SSNIMC), Kishoreganj.

The bot runs as a small **Flask** web app and the answers come from a
**CrewAI agent crew** (one Agent → one Task → sequential Process) that runs
**on your own computer**.

## No API key needed

There is no API key, no `.env` file, no Groq/OpenAI account and no internet
connection involved. Install the packages, start the server and chat — the bot
works offline and is free to run.

---

## Features

- Web chat interface (HTML + CSS + vanilla JS, no build step)
- Conversation memory while the server is running
- Quick-question buttons, so you can start with one click
- "New chat" button to reset the conversation
- Friendly answers for questions it cannot answer (it never invents facts)
- Runs on `localhost:5000` and is reachable from other devices on your Wi-Fi

---

## How the "Crew Agent AI" works

| Part | File | Job |
|------|------|-----|
| `BIO_DATA` / `PROFILE` | `chatbot.py` | Every field of her official HRIS Bio-Data record, stored as structured data and rendered for the agent |
| `KNOWLEDGE` | `chatbot.py` | Topic entries that turn a question into an answer from that data |
| `LocalAgentBrain` | `chatbot.py` | Matches your question to a topic and writes the reply |
| `LocalCrewLLM` | `chatbot.py` | The language model that CrewAI drives — answered locally, never over the network |
| `build_crew()` | `chatbot.py` | Builds the CrewAI Agent, Task and Crew |
| `ChatSession` | `chatbot.py` | Keeps the conversation history, exposes `send()` / `reset()` |
| `app.py` | `app.py` | Flask server with the routes `/`, `/chat`, `/reset`, `/health` |

Each message is passed to a real CrewAI crew; the crew's "LLM" is a small
local component that turns the question into an in-character reply. CrewAI's
telemetry is switched off, so the app makes no outward network calls.

---

## Requirements

- Python 3.10 or newer (the code uses `str | None` style type hints)
- No API key, no account, no credit card
- Optional: `crewai` + `langchain-core` — the bot's answers come from the same
  local brain with or without it, so the cloud build on Render skips them to
  stay fast and inside the free plan's 512 MB memory limit

---

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

   There is nothing else to configure — no key, no `.env` file.

   Optional (to run the full CrewAI crew locally, exactly as described above):

   ```bash
   python -m pip install "crewai==0.11.2" "langchain-core>=0.1.42,<0.2"
   ```

   The replies are identical either way — every answer is written by the local
   brain in `chatbot.py`.

| Variable | Meaning | Example |
|----------|---------|---------|
| `PORT` | Port the Flask server listens on (optional) | `5000` |

---

## Run

```bash
python app.py
```

Then open <http://localhost:5000> in your browser. Check
<http://localhost:5000/health> if you want to confirm the server is alive.

To stop the server, press **CTRL+C** in the terminal.

> Tip: the server binds to `0.0.0.0`, so devices on the same Wi-Fi/LAN can
> reach it at `http://<this-computer-ip>:5000`.

---

## What you can ask

- Who are you?
- Who is Dr. Sumaiya Mohammad? / Tell me about her
- What is her designation / department?
- Where does she work? Since when?
- Which school and college did she attend?
- Was she a hostel superintendent?
- What committees is she a member of?
- What is her role in the Bangladesh Society of Physiologists?
- What is her father's / mother's name?
- What is her religion? When was she born?
- What is her mobile number / email address / NID?
- What is her permanent address? Where does she live?
- What is her marital status? Is she a freedom fighter?
- What is her BCS batch / job status / staff professional category?
- What is her highest degree (MD, Physiology)?
- What is her basic pay / pay scale / post ID?
- Tell me about her government service record / HRIS Bio-Data
- Show me all her information

---

## Changing the answers

Everything the bot knows lives in `chatbot.py`:

- `BIO_DATA` – a structured dictionary with every field of her official HRIS
  Bio-Data record (personal information, other information, service record and
  education). Edit a value here once and every answer that uses it updates.
- `PROFILE` – generated from `BIO_DATA` by `_format_bio_data()`; the plain-text
  profile used as the agent's backstory.
- `KNOWLEDGE` – a tuple of `Topic(name, keywords, answer)` entries. Add a
  topic, add keywords to an existing one, or edit an answer. Multi-word
  keywords match more strongly than single words, and small typos in the
  question are tolerated automatically.

---

## Tests

```bash
python test_chatbot.py
```

The checks run entirely offline: they exercise the brain, the CrewAI crew, the
Flask routes and the "no API key anywhere" rule. When the server is already
running, the same script also checks it live over HTTP. The script exits with a
non-zero status if any check fails.

---

## Deploy on Render (optional)

`render.yaml` in this repository is a Render **Blueprint** that describes a free
Python web service. No API key or secret has to be configured in the cloud
either - the app is completely self-contained.

Two files make the cloud build work:

- `.python-version` (and the matching `PYTHON_VERSION` env var) - the Python
  version the service builds with, because `crewai` needs Python 3.10 or newer.
- `gunicorn` in `requirements.txt` - the production web server used in the
  cloud. It is installed only on Linux; on Windows you keep using
  `python app.py`.

### With the Render CLI

```bash
# Authenticate once (or set RENDER_API_KEY in your environment)
render login

render services create \
  --name crew-agent-ai \
  --type web_service \
  --repo https://github.com/sumaiyamohammadwajeeh2019/chatbot \
  --branch main \
  --runtime python \
  --plan free \
  --region singapore \
  --build-command "pip install -r requirements.txt" \
  --start-command "gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120" \
  --health-check-path /health \
  --env-var PYTHON_VERSION=3.11.9 \
  --confirm

# Watch the build, then read the logs
render deploys create <service-id> --wait
render logs --resources <service-id>
```

The service is live at `https://<service-name>.onrender.com`, and `/health` is
used as the health check. Every push to `main` redeploys it automatically
(auto-deploy).

### From the dashboard instead

**New +** then **Blueprint**, pick this repository, and Render reads `render.yaml`
and creates the same service.

> Free instances sleep after about 15 minutes without traffic and take roughly a
> minute to wake again on the next request.

> The Render build installs only Flask and Gunicorn. The optional CrewAI
> packages are skipped there, so the build finishes in under a minute and the
> service boots comfortably inside the free plan's 512 MB memory limit.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Address already in use` | Another program (often an old copy of this app) is using port 5000. Stop it, or run with another port: `set PORT=5001` then `python app.py` |
| Browser shows "can't reach this page" | Make sure the terminal still shows the server running, then reload <http://localhost:5000> |
| `ModuleNotFoundError: crewai` | Optional package: the app works without it. To run the CrewAI crew locally: `python -m pip install "crewai==0.11.2" "langchain-core>=0.1.42,<0.2"` |
| A pydantic warning about V1/V2 models on start-up | Harmless: it comes from CrewAI's own LangChain integration and is filtered out by `chatbot.py` |

---

## Privacy

- No API key or secret is stored anywhere in this project.
- Nothing is sent to the internet: the answers are generated on this computer
  (CrewAI telemetry is disabled).
- Conversations live only in memory and disappear when the server stops.

---

## About Dr. Sumaiya Mohammad

- Designation: Assistant Professor
- Department: Department of Physiology
- Institution: Shaheed Syed Nazrul Islam Medical College, Kishoreganj
- Joined the institution: 24-10-2021 (Assistant Professor since 16-03-2022)
- School: Monipur High School
- College: Viqarunnisa Noon College
- Degrees: MBBS (2011) · MD (Physiology, 2020)

### Personal information (official HRIS Bio-Data)

- Father's name: Md. Abul Bashar Sarker · Mother's name: Khaleda Qusem
- Date of birth: 01-01-1988 · Sex: Female · Marital status: Married
- Religion: Islam · Tribe: Not Tribal · Freedom fighter: Yes
- Lives in a government quarter: No · Professional discipline: Physiology
- Mobile: 01742701642 · Email: sumaiya.arba@yahoo.com · NID: 4798517233107
- Mailing/present address: Shaheed Syed Nazrul Islam Medical College,
  Sadar, Kishoreganj
- Permanent address: Vill- Mehar, Maijkhar, PO- Badorpur Bazar,
  Upazila- Chandina, Dist- Comilla
- PRL date: 01-01-2048

### Government service record (official HRIS Bio-Data)

- BCS (Health) cadre, BCS Batch No 32; staff professional category: Physician
- HRIS ID: 89222 · Post ID: 165084 · Doctor Code No: 128339
- Original designation: Medical Officer (MO)
- Status: Posted, posted as Current Charge · Joining back verified: 1
- Joined government health service: 30-10-2013 (first appointment 08-10-2013)
- Service confirmed: 30-10-2013 (Confirmation GO No
  45.143.069.02.00.003.2016-385, SL No 1178, dated 20-06-2017)
- Joined current place (SSNIMC): 24-10-2021 · current designation
  (Assistant Professor, Physiology): 16-03-2022
- Two study deputations in total; earlier record: study deputation at
  Bangabandhu Sheikh Mujib Medical University (BSMMU), Dhaka
- Post pay scale 6, current payscale hold 9, basic pay 35,880; ACRs 2014–2020

### Working experience & responsibilities

- Hostel Superintendent of Shila Islam Ladies Hostel, SSNIMC, Kishoreganj
- Member of the Hostel Disciplinary Committee, SSNIMC
- Member of the Antiragging Committee, SSNIMC
- Member of the Pair Medical College Visiting Committee, SSNIMC
- Member of the Medical Education Unit, SSNIMC
- Vice President of the Mymensingh region, Bangladesh Society of Physiologists
- Member of the Education Sub-committee, Operational Manual Reform Sub-committee
  and Teachers Benefit Sub-committee of the Bangladesh Society of Physiologists