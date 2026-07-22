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


def make_llm_backend(settings: AriaSettings) -> LLMBackend:
    if settings.llm_backend == "echo":
        return EchoLLM()
    return OllamaLLM(host=settings.ollama_host, model=settings.model)
