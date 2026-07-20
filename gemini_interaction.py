"""Direct Gemini API client for calling Google Gemini from code.

Companion to the Anthropic/Claude pipeline in ``video_tool/analyzer.py``. Where
``COORDINATION.md`` and ``squad`` give ARIA an *async* (git-based) channel to a
Gemini agent, this module is the *synchronous* path: call Gemini directly and
get text back in the same process.

Usage:
    from gemini_interaction import get_gemini_response
    print(get_gemini_response("Summarize this repo in one sentence."))

    # or from the shell:
    #   export GEMINI_API_KEY=...        # (GOOGLE_API_KEY also accepted)
    #   python gemini_interaction.py "Write a haiku about video analysis."

Requires the official Google Gen AI SDK:  pip install google-genai
"""
from __future__ import annotations

import os
import sys

# Default model — Gemini 2.5 Flash: fast, cheap, multimodal. Override with the
# GEMINI_MODEL env var or the `model` argument.
DEFAULT_MODEL = "gemini-2.5-flash"


def _get_api_key() -> str:
    """Return the Gemini API key, preferring GEMINI_API_KEY over GOOGLE_API_KEY."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "Set GEMINI_API_KEY (or GOOGLE_API_KEY) in your environment. "
            "Get a key at https://aistudio.google.com/apikey"
        )
    return api_key


def _get_client():
    """Build a Gen AI client, with a clear message if the SDK is missing."""
    try:
        from google import genai
    except ImportError as exc:  # pragma: no cover - import-time guard
        raise ImportError(
            "The google-genai SDK is not installed. Run: pip install google-genai"
        ) from exc
    return genai.Client(api_key=_get_api_key())


def get_gemini_response(
    prompt: str,
    model: str | None = None,
    system_instruction: str | None = None,
) -> str:
    """Send a prompt to Gemini and return the text response.

    Parameters:
        prompt: The user prompt to send.
        model: Model id (defaults to $GEMINI_MODEL or ``gemini-2.5-flash``).
        system_instruction: Optional system prompt to steer the model.

    Returns:
        The model's text response.
    """
    if not prompt or not prompt.strip():
        raise ValueError("prompt must be a non-empty string.")

    client = _get_client()
    model = model or os.getenv("GEMINI_MODEL") or DEFAULT_MODEL

    config = None
    if system_instruction:
        from google.genai import types

        config = types.GenerateContentConfig(system_instruction=system_instruction)

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=config,
    )

    text = getattr(response, "text", None)
    if not text:
        raise RuntimeError(
            f"Gemini returned no text (model={model}). "
            "The prompt may have been blocked or the response empty."
        )
    return text


if __name__ == "__main__":
    user_prompt = " ".join(sys.argv[1:]) or "Write a short poem about the stars."
    try:
        print(f"Sending prompt to Gemini: {user_prompt}")
        print("Response from Gemini:", get_gemini_response(user_prompt))
    except Exception as exc:  # surface a clean message, not a traceback
        print("An error occurred:", exc)
        sys.exit(1)
