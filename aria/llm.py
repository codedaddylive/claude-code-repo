from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import Iterator

import httpx

from .config import AriaSettings
from .models import BackendError, ChatMessage


class LLMBackend(ABC):
    """A chat-completion backend for an open-source language model."""

    @abstractmethod
    def chat(self, messages: list[ChatMessage], *, temperature: float = 0.2) -> str:
        """Return the assistant's full reply."""

    def stream(
        self, messages: list[ChatMessage], *, temperature: float = 0.2
    ) -> Iterator[str]:
        """Yield the reply in chunks. Default: emit the full reply at once."""
        yield self.chat(messages, temperature=temperature)


class EchoLLM(LLMBackend):
    """Offline stub backend.

    It performs no generation; it echoes the retrieved context and question so
    the full pipeline (ingest → retrieve → prompt) can be exercised in tests and
    demos without a model server. Swap in :class:`OllamaLLM` for real answers.
    """

    def chat(self, messages: list[ChatMessage], *, temperature: float = 0.2) -> str:
        user = next((m.content for m in reversed(messages) if m.role == "user"), "")
        return (
            "[echo backend — no model server configured]\n"
            "I received your question and the retrieved context below. Configure "
            "an Ollama model (ARIA_LLM_BACKEND=ollama) for a real answer.\n\n"
            f"{user}"
        )


class OllamaLLM(LLMBackend):
    """Chat completions from a local Ollama server."""

    def __init__(self, host: str, model: str, timeout: float = 300.0) -> None:
        self.host = host.rstrip("/")
        self.model = model
        self.timeout = timeout

    def _payload(self, messages: list[ChatMessage], temperature: float, stream: bool) -> dict:
        return {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": stream,
            "options": {"temperature": temperature},
        }

    def chat(self, messages: list[ChatMessage], *, temperature: float = 0.2) -> str:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    f"{self.host}/api/chat",
                    json=self._payload(messages, temperature, stream=False),
                )
                resp.raise_for_status()
                return resp.json()["message"]["content"]
        except (httpx.HTTPError, KeyError) as e:
            raise BackendError(
                f"Ollama chat request failed ({e}). Is Ollama running at "
                f"{self.host} with model '{self.model}' pulled?"
            ) from e

    def stream(
        self, messages: list[ChatMessage], *, temperature: float = 0.2
    ) -> Iterator[str]:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                with client.stream(
                    "POST",
                    f"{self.host}/api/chat",
                    json=self._payload(messages, temperature, stream=True),
                ) as resp:
                    resp.raise_for_status()
                    for line in resp.iter_lines():
                        if not line:
                            continue
                        data = json.loads(line)
                        piece = data.get("message", {}).get("content", "")
                        if piece:
                            yield piece
                        if data.get("done"):
                            break
        except (httpx.HTTPError, json.JSONDecodeError, KeyError) as e:
            raise BackendError(
                f"Ollama stream request failed ({e}). Is Ollama running at "
                f"{self.host} with model '{self.model}' pulled?"
            ) from e


def parse_openai_chat(data: dict) -> str:
    """Extract the assistant message from an OpenAI-style chat response."""
    return data["choices"][0]["message"]["content"]


def parse_openai_stream_line(line: str) -> str | None:
    """Parse one SSE line from an OpenAI-style stream into a text delta.

    Returns the delta string, or ``None`` for keep-alive / non-content lines.
    Raises ``StopIteration`` semantics via the sentinel ``"[DONE]"`` handled by
    the caller.
    """
    line = line.strip()
    if not line or not line.startswith("data:"):
        return None
    payload = line[len("data:"):].strip()
    if payload == "[DONE]":
        return None
    data = json.loads(payload)
    # Some providers (e.g. NVIDIA NIM) send a final chunk with an empty
    # "choices" list (usage-only) — treat it as a non-content line.
    choices = data.get("choices") or []
    if not choices:
        return None
    return choices[0].get("delta", {}).get("content")


class OpenAICompatLLM(LLMBackend):
    """Chat completions from any OpenAI-compatible hosted provider.

    Works with Together, OpenRouter, Groq, Fireworks, a self-hosted vLLM, etc.
    All of these serve open-source models — Aria stays open, the GPUs are just
    someone else's.
    """

    def __init__(self, base_url: str, api_key: str, model: str, timeout: float = 300.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def _payload(self, messages: list[ChatMessage], temperature: float, stream: bool) -> dict:
        return {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "stream": stream,
        }

    def chat(self, messages: list[ChatMessage], *, temperature: float = 0.2) -> str:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json=self._payload(messages, temperature, stream=False),
                )
                resp.raise_for_status()
                return parse_openai_chat(resp.json())
        except (httpx.HTTPError, KeyError, IndexError) as e:
            raise BackendError(
                f"Hosted chat request to {self.base_url} failed ({e}). Check "
                f"ARIA_API_KEY and that model '{self.model}' is valid for the provider."
            ) from e

    def stream(
        self, messages: list[ChatMessage], *, temperature: float = 0.2
    ) -> Iterator[str]:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json=self._payload(messages, temperature, stream=True),
                ) as resp:
                    resp.raise_for_status()
                    for line in resp.iter_lines():
                        piece = parse_openai_stream_line(line)
                        if piece:
                            yield piece
        except (httpx.HTTPError, json.JSONDecodeError, KeyError, IndexError) as e:
            raise BackendError(
                f"Hosted stream request to {self.base_url} failed ({e}). Check "
                f"ARIA_API_KEY and that model '{self.model}' is valid for the provider."
            ) from e


def make_llm_backend(settings: AriaSettings) -> LLMBackend:
    if settings.llm_backend == "echo":
        return EchoLLM()
    if settings.llm_backend == "openai":
        if not settings.api_key:
            raise BackendError(
                "ARIA_LLM_BACKEND=openai requires ARIA_API_KEY to be set."
            )
        return OpenAICompatLLM(
            base_url=settings.api_base_url, api_key=settings.api_key, model=settings.model
        )
    return OllamaLLM(host=settings.ollama_host, model=settings.model)
