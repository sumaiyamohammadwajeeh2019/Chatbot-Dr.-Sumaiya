"""
Personal chatbot core for Dr. Sumaiya Mohammad.

This module loads the GROQ_API_KEY from the .env file and provides:
  - The system prompt that gives the bot Dr. Sumaiya Mohammad's personal
    and professional background.
  - A ChatSession class that manages the conversation history and talks
    to the Groq API.
"""

import os

from dotenv import load_dotenv
from groq import Groq

# Load environment variables from the .env file at the project root.
load_dotenv()

# ---------------------------------------------------------------------------
# Personal profile of Dr. Sumaiya Mohammad (used in the system prompt)
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
- Served as a member of the Hostel Disciplinary Committee of the medical college.
- Served as a member of the Antiragging Committee of the medical college.
- Current member of the Pair Medical College Visiting Committee, SSNIMC.
- Current member of the Medical Education Unit of SSNIMC.
- Posted as the Vice President of the Mymensingh region of the Bangladesh
  Society of Physiologists.
- Member of the Education Sub-committee, Operational Manual Reform Sub-committee
  and Teachers Benefit Sub-committee of the Bangladesh Society of Physiologists.
"""

SYSTEM_PROMPT = f"""
You are a friendly and professional personal assistant chatbot for Dr. Sumaiya Mohammad.

Here is Dr. Sumaiya Mohammad's personal and professional information:
{PROFILE}

Guidelines:
- When asked about her identity, designation, workplace, or educational
  background, answer accurately and warmly based on the information above.
- Speak in first person as if you are Dr. Sumaiya Mohammad's personal
  assistant. For example, when asked "Who are you?", say something like:
  "I am a personal assistant chatbot for Dr. Sumaiya Mohammad...".
- Keep responses clear, concise, and helpful. Use a warm, professional tone.
- If asked something you do not know about her, politely say you don't have
  that information rather than guessing.
"""


class ChatSession:
    """Holds conversation history and communicates with the Groq API."""

    def __init__(self, model: str | None = None, temperature: float = 0.7):
        api_key = os.getenv("GROQ_API_KEY", "").strip()
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY is missing. Please create a .env file in the "
                "project folder with: GROQ_API_KEY=your_groq_api_key"
            )
        self._client = Groq(api_key=api_key)
        self.model = model or os.getenv("MODEL", "openai/gpt-oss-20b")
        self.temperature = temperature
        self._history: list[dict] = []

    def reset(self) -> None:
        """Clear the conversation history."""
        self._history = []

    def _messages(self) -> list[dict]:
        """System prompt followed by the current conversation history."""
        return [{"role": "system", "content": SYSTEM_PROMPT}] + self._history

    def send(self, user_message: str) -> str:
        """Send one user message and return the assistant's reply."""
        self._history.append({"role": "user", "content": user_message})

        response = self._client.chat.completions.create(
            model=self.model,
            messages=self._messages(),
            temperature=self.temperature,
        )

        reply = response.choices[0].message.content or ""
        self._history.append({"role": "assistant", "content": reply})
        return reply