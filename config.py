import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from the project root.
BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")


def get_int_setting(name, default, minimum=1):
    """Read and validate an integer environment variable."""
    value = os.getenv(name, str(default))

    try:
        result = int(value)
    except ValueError as exc:
        raise ValueError(
            f"{name} must be an integer."
        ) from exc

    if result < minimum:
        raise ValueError(
            f"{name} must be at least {minimum}."
        )

    return result


def get_float_setting(name, default, minimum, maximum):
    """Read and validate a floating-point environment variable."""
    value = os.getenv(name, str(default))

    try:
        result = float(value)
    except ValueError as exc:
        raise ValueError(
            f"{name} must be a number."
        ) from exc

    if not minimum <= result <= maximum:
        raise ValueError(
            f"{name} must be between {minimum} and {maximum}."
        )

    return result


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-2.5-flash",
).strip()

GEMINI_TEMPERATURE = get_float_setting(
    "GEMINI_TEMPERATURE",
    default=0.7,
    minimum=0.0,
    maximum=2.0,
)

MAX_HISTORY_MESSAGES = get_int_setting(
    "MAX_HISTORY_MESSAGES",
    default=20,
)

MAX_INPUT_CHARACTERS = get_int_setting(
    "MAX_INPUT_CHARACTERS",
    default=10000,
)

MAX_RETRIES = get_int_setting(
    "MAX_RETRIES",
    default=3,
    minimum=0,
)

RETRY_BASE_DELAY = get_float_setting(
    "RETRY_BASE_DELAY",
    default=1.0,
    minimum=0.1,
    maximum=60.0,
)

REQUEST_TIMEOUT_MS = get_int_setting(
    "REQUEST_TIMEOUT_MS",
    default=30000,
)

DATABASE_PATH = os.getenv(
    "DATABASE_PATH",
    str(BASE_DIR / "chat_history.db"),
).strip()

if not DATABASE_PATH:
    DATABASE_PATH = str(BASE_DIR / "chat_history.db")

if DATABASE_PATH != ":memory:":
    DATABASE_PATH = str(
        Path(DATABASE_PATH).expanduser().resolve()
    )