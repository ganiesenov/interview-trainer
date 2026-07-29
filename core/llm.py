"""Thin wrapper around the local Ollama server.

Everything in this project runs offline. The model is never asked to know
anything: it either asks a question from the bank or compares two texts.
"""

from __future__ import annotations

import os

DEFAULT_MODEL = os.getenv("INTERVIEW_MODEL", "qwen2.5:32b-instruct-q4_K_M")
DEFAULT_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")

# The grader must be boring and repeatable; question generation may wander.
GRADER_TEMPERATURE = 0.15
QUESTION_TEMPERATURE = 0.7


class LLMError(RuntimeError):
    """Ollama is unreachable, the model is missing, or the call failed."""


def _client():
    try:
        import ollama
    except ImportError as exc:  # pragma: no cover - trivial
        raise LLMError(
            "The 'ollama' package is not installed. Run: pip install -r requirements.txt"
        ) from exc
    return ollama.Client(host=DEFAULT_HOST)


def chat(
    messages: list[dict],
    *,
    model: str | None = None,
    temperature: float = GRADER_TEMPERATURE,
    json_mode: bool = False,
    num_predict: int | None = None,
) -> str:
    """Send a chat request and return the raw assistant text."""
    model = model or DEFAULT_MODEL
    options = {"temperature": temperature}
    if num_predict is not None:
        options["num_predict"] = num_predict

    try:
        response = _client().chat(
            model=model,
            messages=messages,
            format="json" if json_mode else "",
            options=options,
        )
    except LLMError:
        raise
    except Exception as exc:
        raise LLMError(
            f"Call to Ollama failed ({DEFAULT_HOST}, model {model}): {exc}\n"
            f"Check that the server is running and the model is pulled: ollama pull {model}"
        ) from exc

    return (response.get("message") or {}).get("content", "") or ""
