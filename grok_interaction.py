"""Direct Grok (xAI) API client for calling Grok from code.

Third sibling to ``video_tool/analyzer.py`` (Claude) and ``gemini_interaction.py``
(Gemini). The xAI API is OpenAI-compatible, so this uses the ``openai`` SDK
pointed at ``https://api.x.ai/v1``.

Usage:
    from grok_interaction import get_grok_response
    print(get_grok_response("Summarize this repo in one sentence."))

    # or from the shell:
    #   export XAI_API_KEY=...            # (GROK_API_KEY also accepted)
    #   python grok_interaction.py "Write a haiku about video analysis."

Requires the OpenAI SDK:  pip install openai
"""
from __future__ import annotations

import os
import sys

# xAI's OpenAI-compatible endpoint.
XAI_BASE_URL = "https://api.x.ai/v1"
# Default model. Override with the GROK_MODEL env var or the `model` argument.
DEFAULT_MODEL = "grok-4"


def _get_api_key() -> str:
    """Return the xAI API key, preferring XAI_API_KEY over GROK_API_KEY."""
    api_key = os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "Set XAI_API_KEY (or GROK_API_KEY) in your environment. "
            "Get a key at https://console.x.ai"
        )
    return api_key


def _get_client():
    """Build an OpenAI-compatible client pointed at xAI, with a clear SDK guard."""
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - import-time guard
        raise ImportError(
            "The openai SDK is not installed. Run: pip install openai"
        ) from exc
    return OpenAI(api_key=_get_api_key(), base_url=XAI_BASE_URL)


def get_grok_response(
    prompt: str,
    model: str | None = None,
    system_instruction: str | None = None,
) -> str:
    """Send a prompt to Grok and return the text response.

    Parameters:
        prompt: The user prompt to send.
        model: Model id (defaults to $GROK_MODEL or ``grok-4``).
        system_instruction: Optional system prompt to steer the model.

    Returns:
        The model's text response.
    """
    if not prompt or not prompt.strip():
        raise ValueError("prompt must be a non-empty string.")

    client = _get_client()
    model = model or os.getenv("GROK_MODEL") or DEFAULT_MODEL

    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(model=model, messages=messages)

    if not response.choices:
        raise RuntimeError(f"Grok returned no choices (model={model}).")
    text = response.choices[0].message.content
    if not text:
        raise RuntimeError(
            f"Grok returned no text (model={model}). "
            "The prompt may have been blocked or the response empty."
        )
    return text


if __name__ == "__main__":
    user_prompt = " ".join(sys.argv[1:]) or "Write a short poem about the stars."
    try:
        print(f"Sending prompt to Grok: {user_prompt}")
        print("Response from Grok:", get_grok_response(user_prompt))
    except Exception as exc:  # surface a clean message, not a traceback
        print("An error occurred:", exc)
        sys.exit(1)
