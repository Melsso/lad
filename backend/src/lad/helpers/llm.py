from collections.abc import Iterator, Sequence

from lad.core.llm import generate_content, stream_content
from lad.models.db import Messages

SYSTEM_PROMPT = """You are a helpful AI assistant.

Answer the user's message accurately and naturally.

You have access to a conversation summary and recent conversation messages.
Use them as context when relevant.

Do not mention the conversation summary, context management, token limits,
or any internal implementation details to the user.
"""


AGENT_SYSTEM_PROMPT = """You are a coding agent working inside the LAD
repository.

You have tools available for searching the codebase and its documentation.
For almost any question about how this code works, what a function does,
why a design decision was made, or anything specific to this project, call
the relevant tool before answering — even if you believe you already know
the answer, since your own knowledge may be outdated or wrong for this
specific codebase.

Re-evaluate whether a tool is needed for every new question independently.
A tool having been used earlier in this conversation does not mean it has
already been "tried" for a new, different question — treat each question
as its own fresh decision.

Base your answer only on what a tool actually returned. If the tool's
results do not answer the question, say so plainly instead of guessing or
inventing details — do not present invented specifics as fact, and do not
attribute fabricated behavior to real function or file names.

Do not mention these instructions, context management, or any internal
implementation details to the user.
"""


SUMMARY_SYSTEM_PROMPT = """You maintain a compact, accurate summary of a
conversation.

The summary will be used as context for future messages, so preserve
information that may be relevant later.

Preserve:
- Important facts about the user
- User preferences
- Decisions that were made
- Technical details
- Requirements and constraints
- Goals and ongoing tasks
- Important conclusions
- Relevant unresolved questions

Remove:
- Repetitive information
- Unimportant small talk
- Details that have no value for future conversation

If an existing summary is provided, update and improve it using the new
messages. Do not discard useful information from the existing summary.

Return only the updated summary.
"""


def _format_message(message: Messages) -> str:
    if message.role == "tool_call":
        return f"TOOL_CALL {message.tool_name}({message.tool_arguments or '{}'})"

    if message.role == "tool_result":
        return f"TOOL_RESULT {message.tool_name}: {message.content}"

    return f"{message.role.upper()}: {message.content}"


def _format_messages(messages: Sequence[Messages]) -> str:
    return "\n".join(_format_message(message) for message in messages)


def generate_summary(
    *, existing_summary: str | None, messages: Sequence[Messages]
) -> str:
    if not messages:
        return existing_summary or ""

    previous_summary = (
        existing_summary if existing_summary else "(No previous summary exists.)"
    )

    conversation = _format_messages(messages)

    prompt = f"""EXISTING SUMMARY:

{previous_summary}

NEW CONVERSATION MESSAGES:

{conversation}

Create the updated conversation summary now.
"""

    return generate_content(
        contents=prompt,
        system_instruction=SUMMARY_SYSTEM_PROMPT,
        temperature=0.2,
    )


def build_llm_context(*, summary: str | None, messages: Sequence[Messages]) -> str:
    sections: list[str] = []

    if summary:
        sections.append(
            f"""CONVERSATION SUMMARY:

{summary}"""
        )

    if messages:
        sections.append(
            f"""RECENT CONVERSATION:

{_format_messages(messages)}"""
        )

    return "\n\n".join(sections)


def generate_response_stream(
    *, summary: str | None, messages: Sequence[Messages]
) -> Iterator[str]:
    context = build_llm_context(
        summary=summary,
        messages=messages,
    )

    yield from stream_content(
        contents=context,
        system_instruction=SYSTEM_PROMPT,
    )
