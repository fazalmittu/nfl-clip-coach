"""Conversational NFL game analyst agent."""

from __future__ import annotations

import re
import logging

import anthropic

from services.data import load_data, get_category_summary
from .executor import execute_query

logger = logging.getLogger(__name__)

client = anthropic.Anthropic()
MODEL = "claude-sonnet-4-20250514"

SYSTEM_PROMPT = """\
You are an expert NFL coach and game analyst. You have access to play-by-play \
data for NFL games loaded in a pandas DataFrame called `df`.

When the user asks a question that requires data analysis, write Python/pandas \
code to answer it. Put the code in a ```python code block. The code MUST assign \
its final answer to a variable called `result`.

Available column categories:
{categories}

When you don't need data analysis (e.g. general football questions), just \
answer directly without code.
"""


# In-memory session store: session_id -> list of message dicts
_sessions: dict[str, list[dict]] = {}


def _get_session(session_id: str) -> list[dict]:
    if session_id not in _sessions:
        _sessions[session_id] = []
    return _sessions[session_id]


def chat(session_id: str, message: str) -> str:
    """Process a chat message and return the assistant's response."""
    history = _get_session(session_id)
    history.append({"role": "user", "content": message})

    system = SYSTEM_PROMPT.format(categories=get_category_summary())

    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=system,
        messages=history,
    )

    assistant_text = response.content[0].text

    # Check for python code block
    code_match = re.search(r"```python\n(.*?)```", assistant_text, re.DOTALL)
    if code_match:
        code = code_match.group(1).strip()
        df = load_data()
        query_result = execute_query(code, df)

        # Ask Claude to summarize the result
        summary_response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system="You are an NFL analyst. Summarize the data result concisely for the user.",
            messages=[
                {"role": "user", "content": f"Question: {message}\n\nData result:\n{query_result}"},
            ],
        )
        final_answer = summary_response.content[0].text
        history.append({"role": "assistant", "content": final_answer})
        return final_answer

    history.append({"role": "assistant", "content": assistant_text})
    return assistant_text
