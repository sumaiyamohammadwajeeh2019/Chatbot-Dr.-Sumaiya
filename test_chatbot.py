"""Offline tests for Crew Agent AI.

Everything here runs without an API key and without internet access:

    python test_chatbot.py

One line is printed per check and the script exits with a non-zero status if
anything fails, so it also works in automation.
"""

from __future__ import annotations

import inspect
import json
import os
import socket
import threading
import urllib.request

# Prove that the chatbot needs no API key at all.
os.environ.pop("GROQ_API_KEY", None)
os.environ.pop("OPENAI_API_KEY", None)

import chatbot  # noqa: E402
from app import MAX_MESSAGE_LENGTH, app  # noqa: E402

FAILURES = []
CHECKS = 0

PROJECT_FILES = (
    "chatbot.py",
    "app.py",
    "main.py",
    "README.md",
    "requirements.txt",
    "templates/index.html",
    "static/style.css",
)


def check(name: str, condition: bool, detail: str = "") -> None:
    """Record and report the result of one check."""
    global CHECKS
    CHECKS += 1
    suffix = f"  {detail}" if detail and not condition else ""
    print(("PASS  " if condition else "FAIL  ") + name + suffix)
    if not condition:
        FAILURES.append(name)


def contains(reply: str, *needles: str) -> bool:
    """True when every needle appears in the reply, ignoring case."""
    low = reply.lower()
    return all(needle.lower() in low for needle in needles)


def raises_value_error(session: "chatbot.ChatSession", message: str) -> bool:
    """True when send() rejects the message with a ValueError."""
    try:
        session.send(message)
    except ValueError:
        return True
    except Exception:
        return False
    return False


print("=== answers from the brain (no API key) ===")
brain = chatbot.LocalAgentBrain()
CASES = (
    ("Who are you?", ("crew agent ai",)),
    ("Who is Dr. Sumaiya Mohammad?", ("assistant professor", "physiology")),
    ("What is her designation?", ("assistant professor",)),
    ("Which department does she work in?", ("department of physiology",)),
    ("Where does she work?", ("nazrul islam medical college", "kishoreganj")),
    ("Since when has she been working there?", ("2023",)),
    ("Which school did she go to?", ("monipur high school",)),
    ("Which college did she study at?", ("viqarunnisa noon college",)),
    ("What is her educational background?", ("monipur", "viqarunnisa")),
    ("Was she a hostel superintendent?", ("shila islam",)),
    ("Was she on the antiragging committee?", ("antiragging",)),
    ("Is she in the Medical Education Unit?", ("medical education unit",)),
    (
        "What is her role in the society of physiologists?",
        ("vice president", "mymensingh"),
    ),
    ("Tell me about her work experience", ("hostel superintendent",)),
    ("What is her father's name?", ("abul bashar sarker",)),
    ("What is her mother's name?", ("khaleda qusem",)),
    ("Who were her parents?", ("abul bashar sarker", "khaleda qusem")),
    ("What is her religion?", ("islam",)),
    ("What is her mobile number?", ("01742701642",)),
    ("What is her phone number?", ("01742701642",)),
    ("What is her email address?", ("sumaiya.arba@yahoo.com",)),
    ("What is her NID number?", ("4798517233107",)),
    ("When was she born?", ("01-01-1988",)),
    ("How old is she?", ("1988",)),
    ("When is her PRL date?", ("31-12-2047",)),
    ("What is her sex?", ("female",)),
    ("Is she married?", ("married",)),
    ("What is her permanent address?", ("chandina", "comilla")),
    ("What is her mailing address?", ("dghs",)),
    ("Where does she live?", ("osd, dghs",)),
    ("Is she a freedom fighter?", ("freedom fighter",)),
    ("Does she live in a government quarter?", ("govt. quarter: no",)),
    ("What is her tribe?", ("not tribal",)),
    ("What is her staff professional category?", ("physician",)),
    ("What is her job status?", ("cadre",)),
    ("What is her professional discipline?", ("n/a", "physician")),
    ("Does she have village experience?", ("30 october 2013",)),
    ("Show me all her information", ("89222", "01742701642", "abul bashar")),
    ("How can I reach her?", ("01742701642", "sumaiya.arba@yahoo.com")),
    ("Hello", ("hello",)),
    ("Thank you", ("welcome",)),
)
for question, needles in CASES:
    answer = brain.answer(question)
    check(
        f"brain: {question}",
        contains(answer, *needles),
        f"-> {answer[:100]!r}",
    )

answer = brain.answer("What is her favourite food?")
check(
    "brain: unknown question is not invented",
    contains(answer, "don't have"),
    f"-> {answer[:100]!r}",
)

answer = brain.answer("tell me about her edukation")
check(
    "brain: tolerates a typo",
    contains(answer, "monipur"),
    f"-> {answer[:100]!r}",
)

print("=== the CrewAI agent ===")
session = chatbot.ChatSession()
first = session.send("Who are you?")
check("crewai: reply produced", bool(first.strip()), f"-> {first[:100]!r}")
check(
    "crewai: CrewAI engine used",
    session.last_engine == "crewai",
    f"-> {session.last_engine}",
)
second = session.send("And where does she work?")
check(
    "crewai: keeps the conversation going",
    contains(second, "kishoreganj"),
    f"-> {second[:100]!r}",
)
check("crewai: history has 4 entries", len(session.history) == 4)
check("crewai: empty message rejected", raises_value_error(session, "   "))
session.reset()
check("crewai: reset clears the history", session.history == [])

print("=== two conversations at the same time ===")
shared = chatbot.ChatSession()
replies = []


def ask(question: str) -> None:
    replies.append(shared.send(question))


threads = [
    threading.Thread(target=ask, args=("Who are you?",)),
    threading.Thread(target=ask, args=("Where does she work?",)),
]
for thread in threads:
    thread.start()
for thread in threads:
    thread.join()
check("crewai: both concurrent replies produced", len(replies) == 2 and all(replies))

print("=== web app ===")
client = app.test_client()
home = client.get("/")
html = home.get_data(as_text=True)
check("web: GET / serves the UI", home.status_code == 200 and "chatWindow" in html)
check("web: page is branded Crew Agent AI", "Crew Agent AI" in html)

chat_page = client.post("/chat", json={"message": "Who are you?"})
body = chat_page.get_json() or {}
check(
    "web: POST /chat answers",
    chat_page.status_code == 200 and bool(body.get("reply")),
)
check("web: POST /chat with no JSON body", client.post("/chat").status_code == 400)
check(
    "web: POST /chat with an empty message",
    client.post("/chat", json={"message": "  "}).status_code == 400,
)
check(
    "web: POST /chat with a JSON array",
    client.post("/chat", json=[1, 2, 3]).status_code == 400,
)
long_message = client.post(
    "/chat", json={"message": "x" * (MAX_MESSAGE_LENGTH + 20)}
)
check("web: over-long message is trimmed, not rejected", long_message.status_code == 200)
reset = client.post("/reset")
check(
    "web: POST /reset",
    reset.status_code == 200 and reset.get_json() == {"ok": True},
)
health = client.get("/health")
check(
    "web: GET /health",
    health.status_code == 200 and (health.get_json() or {}).get("status") == "ok",
)

print("=== no API key anywhere in the project ===")
for name in PROJECT_FILES:
    if not os.path.exists(name):
        check(f"file present: {name}", False)
        continue
    with open(name, encoding="utf-8") as handle:
        text = handle.read()
    check(f"no API key reference in {name}", "GROQ" not in text and "gsk_" not in text)

source = inspect.getsource(chatbot)
check(
    "chatbot.py reads no key from the environment",
    "getenv" not in source and "environ[" not in source,
)

print("=== live server (only when one is running on port 5000) ===")


def server_is_up(host: str = "127.0.0.1", port: int = 5000) -> bool:
    """True when something is listening on the given address."""
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


if server_is_up():
    with urllib.request.urlopen(
        "http://127.0.0.1:5000/health", timeout=10
    ) as response:
        live_health = json.loads(response.read().decode("utf-8"))
    check("live: GET /health", live_health.get("status") == "ok")

    request = urllib.request.Request(
        "http://127.0.0.1:5000/chat",
        data=json.dumps({"message": "Who are you?"}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        live_reply = json.loads(response.read().decode("utf-8"))
    check(
        "live: POST /chat answers",
        "crew agent ai" in (live_reply.get("reply") or "").lower(),
    )
else:
    print("SKIP  live server checks (nothing is listening on port 5000)")

print()
if FAILURES:
    print(f"{len(FAILURES)} of {CHECKS} checks FAILED:")
    for name in FAILURES:
        print(" -", name)
    raise SystemExit(1)
print(f"All {CHECKS} checks passed - no API key was needed.")