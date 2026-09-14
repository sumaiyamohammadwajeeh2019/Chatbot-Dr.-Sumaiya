"""
Crew Agent AI - personal assistant chatbot for Dr. Sumaiya Mohammad.

This module runs entirely on your own computer:

  * no API key to set,
  * no .env file to create,
  * no internet connection needed.

How it works
------------
1. PROFILE and KNOWLEDGE below hold everything the bot knows about
   Dr. Sumaiya Mohammad (plain, editable text).
2. LocalAgentBrain is the bot's brain: it turns a question into an
   in-character reply by matching that question against the knowledge base.
3. LocalCrewLLM wraps the brain in the LangChain LLM interface that CrewAI
   expects, so every reply is produced by a real CrewAI crew - one Agent,
   one Task, sequential Process (the "Crew Agent AI") - with the brain
   acting as the local language model.
4. ChatSession keeps the conversation history and exposes send()/reset().
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

from crewai import Agent, Crew, Process, Task  # noqa: E402
from langchain_core.callbacks.manager import (  # noqa: E402
    CallbackManagerForLLMRun,
)
from langchain_core.language_models.llms import LLM  # noqa: E402

LOGGER = logging.getLogger(__name__)

# Name shown in the web interface and used by the chatbot in its replies.
AGENT_NAME = "Crew Agent AI"
PERSON_NAME = "Dr. Sumaiya Mohammad"


def _disable_crewai_telemetry() -> None:
    """Stop CrewAI from sending anonymous usage data to telemetry.crewai.com.

    CrewAI 0.11.x creates its Telemetry object inside Crew() and exports OTLP
    spans from a background thread unless the exporter is unavailable, so its
    constructor is replaced here with an offline, do-nothing version.
    """
    try:
        # "telemtry" is how CrewAI itself spells the package name.
        from crewai.telemtry import Telemetry

        def _offline_init(self: Any) -> None:
            self.ready = False

        Telemetry.__init__ = _offline_init  # type: ignore[method-assign]
    except Exception:  # pragma: no cover - layout may change between versions
        LOGGER.debug("CrewAI telemetry could not be disabled", exc_info=True)


_disable_crewai_telemetry()

# ---------------------------------------------------------------------------
# Personal profile of Dr. Sumaiya Mohammad
# ---------------------------------------------------------------------------
PROFILE = """
Dr. Sumaiya Mohammad
- Designation : Assistant Professor
- Department  : Department of Physiology
- Institution : Shaheed Syed Nazrul Islam Medical College, Kishoreganj
- Working at the institution since : 2023
- School      : Monipur High School
- College     : Viqarunnisa Noon College

Working Experience & Responsibilities:
- Served as Hostel Superintendent of Shila Islam Ladies Hostel, Shaheed Syed
  Nazrul Islam Medical College, Kishoreganj.
- Served as a member of the Hostel Disciplinary Committee of the medical
  college.
- Served as a member of the Antiragging Committee of the medical college.
- Current member of the Pair Medical College Visiting Committee, SSNIMC.
- Current member of the Medical Education Unit of SSNIMC.
- Posted as the Vice President of the Mymensingh region of the Bangladesh
  Society of Physiologists.
- Member of the Education Sub-committee, Operational Manual Reform
  Sub-committee and Teachers Benefit Sub-committee of the Bangladesh Society
  of Physiologists.
"""

SYSTEM_PROMPT = f"""
You are the {AGENT_NAME} - a friendly and professional personal assistant
chatbot for {PERSON_NAME}.

Here is {PERSON_NAME}'s personal and professional information:
{PROFILE}

Guidelines:
- Answer accurately and warmly, in the first person as her personal assistant
  (for example: "She is an Assistant Professor ...").
- Keep replies clear, concise and helpful.
- If you do not know something about her, say so politely instead of guessing.
- Never invent contact details, research work or other personal information.
"""

# ---------------------------------------------------------------------------
# Knowledge base - the only place you need to edit to change what the bot
# can answer. Keywords are matched on the whole question; multi-word keywords
# score higher than single words, and small typos are tolerated.
# ---------------------------------------------------------------------------
OVERVIEW_ANSWER = (
    "She is an Assistant Professor in the Department of Physiology at "
    "Shaheed Syed Nazrul Islam Medical College (SSNIMC), Kishoreganj, and she "
    "has been working there since 2023. She studied at Monipur High School and "
    "at Viqarunnisa Noon College. Alongside her teaching she served as the "
    "Hostel Superintendent of Shila Islam Ladies Hostel and as a member of the "
    "Hostel Disciplinary Committee and of the Antiragging Committee, and she is "
    "currently a member of the Pair Medical College Visiting Committee and of "
    "the Medical Education Unit at SSNIMC. She is also the Vice President of "
    "the Mymensingh region of the Bangladesh Society of Physiologists, and a "
    "member of the Education Sub-committee, the Operational Manual Reform "
    "Sub-committee and the Teachers Benefit Sub-committee of the Bangladesh "
    "Society of Physiologists."
)

UNKNOWN_ANSWER = (
    "I'm sorry, I don't have that information about Dr. Sumaiya Mohammad and "
    "I would rather not guess.\n\n"
    "I can help with her designation, department, institution, educational "
    "background, teaching, and the committees and societies she is part of."
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
    """One thing the bot knows how to answer about Dr. Sumaiya Mohammad."""

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
        "I can tell you about her designation, department and institution, her "
        "educational background, her teaching, and the committees and societies "
        "she works with. I run here on this computer, so no API key and no "
        "internet connection are needed.",
    ),
    Topic(
        "overview",
        (
            "tell me about", "overview", "summary", "summarise", "summarize",
            "introduce", "introduction", "profile", "biography", "bio",
            "background", "describe her", "walk me through", "all about",
            "everything about", "her career",
        ),
        OVERVIEW_ANSWER,
    ),
    Topic(
        "name",
        (
            "dr sumaiya", "sumaiya mohammad", "sumaiya", "her name",
            "full name", "who is she", "who is dr", "her identity",
        ),
        f"Her full name is {PERSON_NAME}. She is an Assistant Professor in the "
        "Department of Physiology at Shaheed Syed Nazrul Islam Medical College, "
        "Kishoreganj.",
    ),
    Topic(
        "designation",
        (
            "designation", "position", "job title", "occupation", "professor",
            "assistant professor", "what does she do", "what is her post",
            "which post", "her rank",
        ),
        "She is an Assistant Professor. Her present designation is Assistant "
        "Professor in the Department of Physiology at Shaheed Syed Nazrul Islam "
        "Medical College, Kishoreganj.",
    ),
    Topic(
        "department",
        (
            "department", "dept", "physiology", "subject", "discipline",
            "faculty", "which subject",
        ),
        "She works in the Department of Physiology at Shaheed Syed Nazrul Islam "
        "Medical College, Kishoreganj - her subject is Physiology.",
    ),
    Topic(
        "institution",
        (
            "institution", "medical college", "ssnimc", "nazrul islam",
            "kishoreganj", "workplace", "work place", "where does she work",
            "where she works", "her workplace", "her office", "posting",
            "posted", "hospital", "which college does she work",
        ),
        "She works at Shaheed Syed Nazrul Islam Medical College (SSNIMC) in "
        "Kishoreganj, and she has been working at the institution since 2023.",
    ),
    Topic(
        "tenure",
        (
            "since when", "how long", "joined", "joining", "since 2023",
            "started working", "years of service", "how many years",
        ),
        "She has been working at Shaheed Syed Nazrul Islam Medical College, "
        "Kishoreganj since 2023.",
    ),
    Topic(
        "school",
        ("school", "monipur", "high school", "schooling"),
        "She studied at Monipur High School.",
    ),
    Topic(
        "college",
        (
            "college", "viqarunnisa", "noon college", "hsc", "intermediate",
            "higher secondary",
        ),
        "She completed her college education at Viqarunnisa Noon College.",
    ),
    Topic(
        "education",
        (
            "education", "educational", "study", "studied", "studies",
            "academic", "qualification", "degree", "where did she study",
        ),
        "She studied at Monipur High School and then at Viqarunnisa Noon "
        "College.",
    ),
    Topic(
        "hostel",
        (
            "hostel", "superintendent", "warden", "shila islam",
            "ladies hostel", "residential",
        ),
        "She served as the Hostel Superintendent of Shila Islam Ladies Hostel "
        "at Shaheed Syed Nazrul Islam Medical College, Kishoreganj.",
    ),
    Topic(
        "disciplinary",
        ("disciplinary committee", "disciplinary", "discipline committee"),
        "She served as a member of the Hostel Disciplinary Committee of "
        "Shaheed Syed Nazrul Islam Medical College.",
    ),
    Topic(
        "antiragging",
        ("antiragging", "anti ragging", "ragging"),
        "She served as a member of the Antiragging Committee of Shaheed Syed "
        "Nazrul Islam Medical College.",
    ),
    Topic(
        "visiting_committee",
        ("pair medical college", "visiting committee", "visiting", "peer medical"),
        "She is currently a member of the Pair Medical College Visiting "
        "Committee, SSNIMC.",
    ),
    Topic(
        "medical_education_unit",
        ("medical education unit", "education unit", "meu"),
        "She is currently a member of the Medical Education Unit of SSNIMC.",
    ),
    Topic(
        "society",
        (
            "physiologists", "bangladesh society", "society of physiologists",
            "vice president", "mymensingh", "vp of",
        ),
        "She is posted as the Vice President of the Mymensingh region of the "
        "Bangladesh Society of Physiologists.",
    ),
    Topic(
        "sub_committees",
        (
            "sub committee", "subcommittee", "sub committees",
            "operational manual", "teachers benefit", "reform sub",
        ),
        "She is a member of the Education Sub-committee, the Operational Manual "
        "Reform Sub-committee and the Teachers Benefit Sub-committee of the "
        "Bangladesh Society of Physiologists.",
    ),
    Topic(
        "responsibilities",
        (
            "responsibility", "responsibilities", "duties", "duty",
            "experience", "work experience", "achievements", "activities",
            "what has she done", "positions held", "her roles",
        ),
        "Alongside her teaching she has held these responsibilities:\n"
        "- Hostel Superintendent of Shila Islam Ladies Hostel, SSNIMC\n"
        "- Member of the Hostel Disciplinary Committee, SSNIMC\n"
        "- Member of the Antiragging Committee, SSNIMC\n"
        "- Current member of the Pair Medical College Visiting Committee, SSNIMC\n"
        "- Current member of the Medical Education Unit, SSNIMC\n"
        "- Vice President of the Mymensingh region, Bangladesh Society of "
        "Physiologists\n"
        "- Member of the Education Sub-committee, the Operational Manual Reform "
        "Sub-committee and the Teachers Benefit Sub-committee of the Bangladesh "
        "Society of Physiologists",
    ),
    Topic(
        "teaching",
        (
            "teach", "teaching", "teaches", "lecture", "lectures", "class",
            "classes", "student", "students", "course", "academic work",
        ),
        "She teaches at the Department of Physiology, Shaheed Syed Nazrul Islam "
        "Medical College, Kishoreganj, where she has been working since 2023.",
    ),
    Topic(
        "contact",
        (
            "contact", "email", "e mail", "phone", "mobile", "number",
            "address", "appointment", "consult", "meet her", "reach her",
            "how can i reach",
        ),
        "I do not have her personal contact details, so I cannot share a phone "
        "number or an email address. The best way to reach her is through the "
        "Department of Physiology at Shaheed Syed Nazrul Islam Medical College, "
        "Kishoreganj.",
    ),
    Topic(
        "research",
        (
            "research", "publication", "publications", "paper", "papers",
            "journal", "article", "articles", "thesis", "projects",
        ),
        "I do not have details of her research work or publications, so I will "
        "not guess. What I can tell you is that she is an Assistant Professor "
        "in the Department of Physiology at Shaheed Syed Nazrul Islam Medical "
        "College, Kishoreganj.",
    ),
    Topic(
        "greeting",
        (
            "hello", "hi", "hey", "assalamu", "assalam", "salam", "greetings",
            "good morning", "good afternoon", "good evening", "namaskar",
        ),
        f"Hello! I am the {AGENT_NAME}, {PERSON_NAME}'s personal assistant. "
        "What would you like to know about her?",
    ),
    Topic(
        "how_are_you",
        (
            "how are you", "how are you doing", "how do you do",
            "how is it going", "whats up", "what is up",
        ),
        f"I am doing well, thank you for asking! I am here to answer questions "
        f"about {PERSON_NAME}. How can I help you?",
    ),
    Topic(
        "thanks",
        ("thank", "thanks", "thank you", "thankyou", "many thanks"),
        f"You are most welcome! If you have any other questions about "
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
    """Answers questions about Dr. Sumaiya Mohammad without any API key."""

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
class LocalCrewLLM(LLM):
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