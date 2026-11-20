import random
import time

from google import genai
from google.genai import types
from google.genai import errors

from config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GEMINI_TEMPERATURE,
    MAX_HISTORY_MESSAGES,
    MAX_INPUT_CHARACTERS,
    MAX_RETRIES,
    RETRY_BASE_DELAY,
    REQUEST_TIMEOUT_MS,
)


SYSTEM_INSTRUCTION = """
You are a helpful, friendly, general-purpose AI assistant.

Your responsibilities:

1. Answer general questions clearly and accurately.
2. Explain difficult concepts in simple language.
3. Use previous messages to understand follow-up questions.
4. Ask clarifying questions when necessary.
5. Admit uncertainty rather than inventing information.
6. Never claim to have performed an action you did not perform.
7. Format answers using headings, lists, and examples when useful.

Be professional, natural, and helpful.
"""


_client = None


def get_client():
    """Create and reuse the Gemini client."""

    global _client

    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is missing. "
            "Add your API key to the .env file."
        )

    if _client is None:
        _client = genai.Client(
            api_key=GEMINI_API_KEY,
            http_options=types.HttpOptions(
                timeout=REQUEST_TIMEOUT_MS,
            ),
        )

    return _client


def prepare_history(history):
    """
    Prepare conversation history for Gemini.

    Only recent valid messages are included.
    The complete conversation remains stored in SQLite.
    """

    valid_messages = []

    for message in history:
        role = message.get("role")
        content = message.get("content", "")

        if role not in ("user", "assistant"):
            continue

        if not isinstance(content, str):
            continue

        content = content.strip()

        if not content:
            continue

        valid_messages.append({
            "role": role,
            "content": content,
        })

    # Keep only the configured number of recent messages.
    valid_messages = valid_messages[-MAX_HISTORY_MESSAGES:]

    # Gemini conversation history should begin with a user message.
    while (
        valid_messages
        and valid_messages[0]["role"] == "assistant"
    ):
        valid_messages.pop(0)

    conversation = []

    for message in valid_messages:
        conversation.append(
            types.Content(
                role=(
                    "user"
                    if message["role"] == "user"
                    else "model"
                ),
                parts=[
                    types.Part.from_text(
                        text=message["content"]
                    )
                ],
            )
        )

    return conversation


def is_retryable_error(error):
    """
    Retry temporary API failures.

    Do not retry authentication failures or invalid requests.
    """

    status_code = getattr(error, "code", None)

    try:
        status_code = int(status_code)
    except (TypeError, ValueError):
        return False

    return status_code in (408, 429, 500, 502, 503, 504)


def generate_reply(history, user_message, client=None):
    """
    Generate an AI response using recent conversation history.

    client is optional and allows tests to use a fake client.
    """

    if not isinstance(user_message, str):
        raise ValueError("The question must be text.")

    user_message = user_message.strip()

    if not user_message:
        raise ValueError("The question cannot be empty.")

    if len(user_message) > MAX_INPUT_CHARACTERS:
        raise ValueError(
            f"Your question is too long. "
            f"The maximum length is {MAX_INPUT_CHARACTERS} characters."
        )

    active_client = client or get_client()

    conversation = prepare_history(history)

    conversation.append(
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(
                    text=user_message
                )
            ],
        )
    )

    request_config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        temperature=GEMINI_TEMPERATURE,
    )

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = active_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=conversation,
                config=request_config,
            )

            answer = response.text

            if not answer or not answer.strip():
                raise RuntimeError(
                    "Gemini returned an empty response."
                )

            return answer.strip()

        except errors.APIError as exc:
            if (
                not is_retryable_error(exc)
                or attempt >= MAX_RETRIES
            ):
                raise

            # Exponential backoff with a small random delay.
            delay = min(
                RETRY_BASE_DELAY * (2 ** attempt),
                30.0,
            )

            delay += random.uniform(0, 0.5)

            time.sleep(delay)

    raise RuntimeError(
        "Unable to generate a response after multiple attempts."
    )