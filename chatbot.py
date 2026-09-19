"""
Crew Agent AI - a personal assistant chatbot skeleton.

This module runs entirely on your own computer:

  * no API key to set,
  * no .env file to create,
  * no internet connection needed.

How it works
------------
1. BIO_DATA is the structured profile store. It is currently EMPTY - this is
   a fresh rebuild. Fill the sections in (personal, other, service,
   education, career_history) and PROFILE renders them for the agent prompt.
2. KNOWLEDGE turns a question into an answer. It currently holds only the
   built-in skeleton topics (greetings, overview, help). Add one Topic()
   per subject and the bot will answer it.
3. LocalAgentBrain is the bot's brain: it matches a question against the
   knowledge base and writes the reply.
4. LocalCrewLLM wraps the brain in the LangChain LLM interface that CrewAI
   expects, so every reply is produced by a real CrewAI crew. CrewAI is
   optional: without the crewai package the same brain answers directly
   (identical replies), which keeps the cloud build (Render) small.
5. ChatSession keeps the conversation history and exposes send()/reset().

How to add data
---------------
* A fact     -> put it in BIO_DATA and render it in _format_bio_data().
* An answer  -> add a Topic(name, keywords, answer) to KNOWLEDGE.
* A summary  -> extend OVERVIEW_ANSWER (the "tell me about" reply).
"""

from __future__ import annotations

import logging
import os
import re
import threading
import warnings
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# Keep CrewAI completely offline: no telemetry, no outward network calls.
# ---------------------------------------------------------------------------
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "false")
os.environ.setdefault("CREWAI_TELEMETRY_OPT_OUT", "true")

# CrewAI 0.11.x is built on LangChain's pydantic-v1 shims, which makes
# pydantic print a harmless "Mixing V1 models and V2 models" warning.
warnings.filterwarnings("ignore", message=".*Mixing V1 models and V2 models.*")

try:
    from crewai import Agent, Crew, Process, Task  # noqa: E402
    from langchain_core.callbacks.manager import (  # noqa: E402
        CallbackManagerForLLMRun,
    )
    from langchain_core.language_models.llms import LLM  # noqa: E402

    CREW_AVAILABLE = True
except Exception:  # crewai/langchain-core are optional extras
    Agent = Crew = Process = Task = LLM = None  # type: ignore[assignment]
    CallbackManagerForLLMRun = None  # type: ignore[assignment]
    CREW_AVAILABLE = False

LOGGER = logging.getLogger(__name__)

if not CREW_AVAILABLE:
    LOGGER.info(
        "crewai/langchain-core are not installed; every question will be "
        "answered from the local brain (the answers are identical)."
    )

# Stand-in base class so LocalCrewLLM can still be defined when the optional
# crewai/langchain-core packages are missing (it is simply never used then).
if CREW_AVAILABLE:
    _LLM_BASE = LLM
else:

    class _LLM_BASE:  # type: ignore[no-redef]
        """Placeholder base; LocalCrewLLM is never used without crewai."""

# Name shown in the web interface and used by the chatbot in its replies.
AGENT_NAME = "Crew Agent AI"

# Whose assistant is this? Replace with the real name when the new profile
# is added (it appears in the web UI and in the bot's replies).
PERSON_NAME = "the Profile Owner"

# ---------------------------------------------------------------------------
# Structured profile - FRESH REBUILD, currently empty.
# Fill the sections in as the new information arrives. Every value is a
# plain string; sections and keys are free-form. PROFILE (below) renders
# whatever has been filled in for the agent's prompt.
# ---------------------------------------------------------------------------
BIO_DATA: Dict[str, Dict[str, str]] = {
    "personal": {
        # "father_name": "",
        # "mother_name": "",
        # "date_of_birth": "",
        # "mobile_no": "",
        # "email": "",
    },
    "other": {
        # "professional_discipline": "",
    },
    "service": {
        # "present_posting": "",
        # "bcs_batch_no": "",
    },
    "education": {
        # "bachelor": "",
        # "masters_degree": "",
    },
    "career_history": {
        # "first_posting": "",
    },
}

# Shorthand sections used by the profile renderer below.
_P = BIO_DATA["personal"]
_O = BIO_DATA["other"]
_S = BIO_DATA["service"]
_E = BIO_DATA["education"]
_C = BIO_DATA["career_history"]


def _section_lines(title: str, section: Dict[str, str]) -> str:
    """Render one BIO_DATA section as '- Key: value' lines (or nothing)."""
    if not section:
        return ""
    body = "".join(
        f"- {key.replace('_', ' ').capitalize()}: {value}\n"
        for key, value in section.items()
    )
    return f"{title}:\n{body}"


def _format_bio_data() -> str:
    """Render every stored profile field as plain text for the agent prompt."""
    blocks = [
        f"{PERSON_NAME}\n"
        "(The profile is being rebuilt - the sections below contain whatever "
        "has been entered so far.)\n",
        _section_lines("Personal Information", _P),
        _section_lines("Other Information", _O),
        _section_lines("Service Record", _S),
        _section_lines("Education", _E),
        _section_lines("Career History", _C),
    ]
    return "\n".join(block for block in blocks if block.strip())


PROFILE = _format_bio_data()

SYSTEM_PROMPT = f"""
You are the {AGENT_NAME} - a friendly and professional personal assistant
chatbot for {PERSON_NAME}.

Here is {PERSON_NAME}'s personal and professional information:
{PROFILE}

Guidelines:
- Answer accurately and warmly, in the first person as her personal assistant
  (for example: "She is an Assistant Professor ...").
- Keep replies clear, concise and helpful.
- Answer questions about the personal information directly from the details
  in the profile above.
- If you do not know something, say so politely instead of guessing.
- Never invent contact details or other personal information.
"""

# ---------------------------------------------------------------------------
# Knowledge base - the only place you need to edit to change what the bot
# can answer. Keywords are matched on the whole question; multi-word keywords
# score higher than single words, and small typos are tolerated.
# ---------------------------------------------------------------------------
OVERVIEW_ANSWER = (
    f"This is the {AGENT_NAME}, the personal assistant chatbot for "
    f"{PERSON_NAME}. The profile is being rebuilt right now, so there is "
    "nothing stored yet - as soon as the new bio-data is added, this answer "
    "will introduce the person in detail."
)

UNKNOWN_ANSWER = (
    "I'm sorry, I don't have that information yet - the knowledge base has "
    "just been rebuilt and is still empty.\n\n"
    "New answers are added by editing BIO_DATA and KNOWLEDGE in chatbot.py. "
    "For now I can only greet you and explain what this chatbot is."
)

FOLLOW_UP_CUES: Tuple[str, ...] = (
    "more", "detail", "details", "elaborate", "explain", "again", "continue",
    "go on", "anything else", "another", "the rest", "what about", "also",
    "and", "summary", "summarise", "summarize",
)

# Minimum score a question must reach before a topic counts as a match.
MIN_SCORE = 1.0
# Related topics scoring at least this share of the best score are answered too.
RELATED_RATIO = 0.6
# Never answer more than this many topics in one reply.
MAX_TOPICS = 3


@dataclass(frozen=True)
class Topic:
    """One thing the bot knows how to answer about the profile owner."""

    name: str
    keywords: Tuple[str, ...]
    answer: str


KNOWLEDGE: Tuple[Topic, ...] = (
    Topic(
        "assistant",
        (
            "who are you", "what are you", "your name", "are you a robot",
            "are you human", "are you real", "are you an ai", "crew agent ai",
            "crew agent", "about you", "what can you do", "what do you do",
            "how can you help", "what can i ask", "help", "options",
        ),
        f"I am the {AGENT_NAME} - {PERSON_NAME}'s personal assistant chatbot. "
        "The knowledge base has just been rebuilt and is empty for now; new "
        "answers are added by editing BIO_DATA and KNOWLEDGE in chatbot.py. "
        "I run here on this computer, so no API key and no internet "
        "connection are needed.",
    ),
    Topic(
        "overview",
        (
            "tell me about", "overview", "summary", "summarise", "summarize",
            "introduce", "introduction", "profile", "biography", "bio",
            "background", "describe", "walk me through", "all about",
            "everything about",
        ),
        OVERVIEW_ANSWER,
    ),
    Topic(
        "empty",
        (
            "empty", "nothing", "rebuild", "rebuilt", "reset data",
            "new data", "add data", "no information",
        ),
        "The chatbot data was wiped for a fresh rebuild. There is no "
        "bio-data or knowledge stored at the moment. Add facts to BIO_DATA "
        "and answers to KNOWLEDGE in chatbot.py, and the bot will answer "
        "them straight away.",
    ),
    Topic(
        "greeting",
        (
            "hello", "hi", "hey", "assalamu", "assalam", "salam", "greetings",
            "good morning", "good afternoon", "good evening", "namaskar",
        ),
        f"Hello! I am the {AGENT_NAME}, {PERSON_NAME}'s personal assistant. "
        "What would you like to know?",
    ),
    Topic(
        "how_are_you",
        (
            "how are you", "how are you doing", "how do you do",
            "how is it going", "whats up", "what is up",
        ),
        "I am doing well, thank you for asking! I am here to answer "
        f"questions about {PERSON_NAME}. How can I help you?",
    ),
    Topic(
        "thanks",
        ("thank", "thanks", "thank you", "thankyou", "many thanks"),
        "You are most welcome! If you have any other questions about "
        f"{PERSON_NAME}, just ask.",
    ),
    Topic(
        "farewell",
        ("bye", "goodbye", "good bye", "see you", "farewell", "khoda hafez"),
        f"Goodbye! Come back any time you have a question about {PERSON_NAME}.",
    ),
)

# ---------------------------------------------------------------------------
# Matching helpers
# ---------------------------------------------------------------------------
_WORD_RE = re.compile(r"[a-z0-9']+")


def _normalise(text: str) -> str:
    """Lower-case text, strip punctuation and collapse repeated spaces."""
    text = text.lower().replace("\u2019", "'")
    text = re.sub(r"[^a-z0-9']+", " ", text)
    return " ".join(text.split())


def _tokens(text: str) -> List[str]:
    """The words of an already normalised question."""
    return _WORD_RE.findall(text)


def _safe_prompt_text(text: str) -> str:
    """Keep user text from being reformatted as a prompt placeholder."""
    return str(text or "").replace("{", "(").replace("}", ")")


def _score_topic(normalised: str, tokens: Sequence[str], topic: Topic) -> float:
    """How well a question matches one topic (0 = no match at all)."""
    score = 0.0
    token_set = set(tokens)
    for keyword in topic.keywords:
        if " " in keyword:
            # Multi-word keywords are much more specific than single words.
            if keyword in normalised:
                score += 3.0 + len(keyword.split())
        elif keyword in token_set:
            score += 1.5
        elif len(keyword) > 4 and any(
            SequenceMatcher(None, keyword, token).ratio() >= 0.85
            for token in token_set
        ):
            # Tolerate small typos, e.g. "physiology" typed as "physiologgy".
            score += 1.0
    return score


# ---------------------------------------------------------------------------
# The brain: question in, in-character reply out. Completely offline.
# ---------------------------------------------------------------------------
class LocalAgentBrain:
    """Answers questions about the profile owner without any API key."""

    def __init__(self) -> None:
        self._last_topics: Tuple[Topic, ...] = ()

    def reset(self) -> None:
        """Forget the topics of the previous question (used by "New chat")."""
        self._last_topics = ()

    def answer(self, question: str) -> str:
        """Return the assistant's reply to one user question."""
        normalised = _normalise(question or "")
        if not normalised:
            return "Please type a question and I will do my best to help."

        tokens = _tokens(normalised)
        scored = [
            (_score_topic(normalised, tokens, topic), topic)
            for topic in KNOWLEDGE
        ]
        best_score = max((score for score, _ in scored), default=0.0)

        if best_score < MIN_SCORE:
            return self._follow_up_or_unknown(normalised, tokens)
        return self._pick_topics(scored, best_score)

    def _pick_topics(self, scored, best_score: float) -> str:
        """Choose the best-matching topics and join their answers."""
        chosen = [
            topic
            for score, topic in sorted(
                scored, key=lambda item: item[0], reverse=True
            )
            if score >= max(MIN_SCORE, best_score * RELATED_RATIO)
        ][:MAX_TOPICS]
        self._last_topics = tuple(chosen)

        answers: List[str] = []
        for topic in chosen:
            if topic.answer not in answers:
                answers.append(topic.answer)
        return "\n\n".join(answers)

    def _follow_up_or_unknown(
        self, normalised: str, tokens: Sequence[str]
    ) -> str:
        """Handle "tell me more" style questions and genuinely unknown ones."""
        looks_like_follow_up = len(tokens) <= 3 or any(
            cue in normalised for cue in FOLLOW_UP_CUES
        )
        if self._last_topics and looks_like_follow_up:
            return (
                "Sure - here is a quick summary:\n\n"
                f"{OVERVIEW_ANSWER}\n\n"
                "Which part would you like me to go into more detail about?"
            )
        return UNKNOWN_ANSWER


# ---------------------------------------------------------------------------
# The CrewAI "language model": a thin LangChain wrapper around the brain.
# ---------------------------------------------------------------------------
class LocalCrewLLM(_LLM_BASE):
    """The model CrewAI drives - answered by LocalAgentBrain, never the net.

    CrewAI talks to its LLM through LangChain and expects a ReAct-style
    answer, so _call() returns "Thought: ... / Final Answer: <reply>".
    """

    brain: Any = None
    question: str = ""

    @property
    def _llm_type(self) -> str:
        """Short identifier used by LangChain."""
        return "crew-agent-ai-local"

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Produce the agent's final answer for the current question."""
        reply = ""
        if self.brain is not None:
            reply = self.brain.answer(self.question)
        reply = (reply or "").strip() or "I am not sure how to answer that yet."
        return f"Thought: I now know the final answer\nFinal Answer: {reply}"


def build_crew(llm: LLM, task_description: str, verbose: bool = False) -> Crew:
    """Build the one-agent crew that produces the assistant's reply."""
    if not CREW_AVAILABLE:
        return None  # type: ignore[return-value]
    agent = Agent(
        role=f"Personal assistant for {PERSON_NAME} ({AGENT_NAME})",
        goal=(
            f"Answer questions about {PERSON_NAME} accurately and warmly, "
            "continuing the conversation naturally."
        ),
        backstory=SYSTEM_PROMPT,
        llm=llm,
        memory=False,
        allow_delegation=False,
        max_iter=3,
        verbose=verbose,
    )
    task = Task(
        description=task_description,
        expected_output="The assistant's next reply as plain text.",
        agent=agent,
    )
    return Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=verbose,
    )


# ---------------------------------------------------------------------------
# Conversation session
# ---------------------------------------------------------------------------
class ChatSession:
    """Holds the conversation history and gets replies from a CrewAI agent."""

    #: How many previous messages are shown to the agent as context.
    MAX_CONTEXT_MESSAGES = 6
    #: Longest single history entry kept in the task prompt.
    MAX_CONTEXT_CHARS = 500

    def __init__(self, verbose: bool = False) -> None:
        self.verbose = verbose
        self.brain = LocalAgentBrain()
        #: Which engine produced the last reply: "crewai" or "local".
        self.last_engine = ""
        self._history: List[Dict[str, str]] = []
        self._lock = threading.Lock()

    # ------------------------------------------------------------ public API
    @property
    def history(self) -> List[Dict[str, str]]:
        """A copy of the conversation so far."""
        with self._lock:
            return [dict(message) for message in self._history]

    def reset(self) -> None:
        """Clear the conversation history."""
        with self._lock:
            self._history = []
            self.brain.reset()
            self.last_engine = ""

    def send(self, user_message: str) -> str:
        """Send one user message to the crew and return the reply."""
        message = (user_message or "").strip()
        if not message:
            raise ValueError("Message cannot be empty.")

        with self._lock:
            self._history.append({"role": "user", "content": message})
            reply = self._reply(message)
            self._history.append({"role": "assistant", "content": reply})
            return reply

    # --------------------------------------------------------------- helpers
    def _reply(self, message: str) -> str:
        """Ask the CrewAI crew for a reply, falling back to the brain."""
        if not CREW_AVAILABLE:
            self.last_engine = "local"
            return self.brain.answer(message)
        try:
            llm = LocalCrewLLM(brain=self.brain, question=message)
            crew = build_crew(
                llm, self._task_description(message), self.verbose
            )
            reply = str(crew.kickoff()).strip()
            if reply:
                self.last_engine = "crewai"
                return reply
            LOGGER.warning("The crew returned an empty reply; using the brain")
        except Exception:
            # Whatever happens above, the chat window never breaks.
            LOGGER.exception("CrewAI run failed; answering from the brain")
        self.last_engine = "local"
        return self.brain.answer(message)

    def _task_description(self, message: str) -> str:
        """The CrewAI task prompt: recent context plus the current message."""
        recent = self._history[-self.MAX_CONTEXT_MESSAGES :]
        lines: List[str] = []
        for entry in recent:
            content = _safe_prompt_text(entry.get("content", ""))
            if content:
                lines.append(
                    f"{entry.get('role', 'user')}: "
                    f"{content[:self.MAX_CONTEXT_CHARS]}"
                )
        transcript = "\n".join(lines)
        return (
            f"Conversation so far:\n{transcript}\n\n"
            f"Latest user message: {_safe_prompt_text(message)}\n\n"
            "Write ONLY the assistant's next reply, in character, as plain "
            "text. Do not repeat the question and do not add any labels."
        )

# ===CHUNK4===
