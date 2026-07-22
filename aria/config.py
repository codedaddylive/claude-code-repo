from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AriaSettings(BaseSettings):
    """Runtime configuration for Aria.

    Every value can be set via an environment variable prefixed with ``ARIA_``
    (e.g. ``ARIA_MODEL=qwen2.5:7b``) or a ``.env`` file in the working directory.
    Sensible defaults are chosen so Aria works out of the box against a local
    Ollama install, and falls back to a fully offline mode when no backend is
    reachable.
    """

    model_config = SettingsConfigDict(env_prefix="ARIA_", env_file=".env", extra="ignore")

    # --- LLM backend -------------------------------------------------------
    llm_backend: Literal["ollama", "openai", "echo"] = Field(
        default="ollama",
        description="Which LLM backend to use. 'ollama' talks to a local Ollama "
        "server; 'openai' talks to any OpenAI-compatible hosted provider "
        "(Together, OpenRouter, Groq, vLLM, ...); 'echo' is an offline stub.",
    )
    ollama_host: str = Field(
        default="http://localhost:11434",
        description="Base URL of the Ollama server.",
    )
    model: str = Field(
        default="llama3.1:8b",
        description="Open-source chat model. For Ollama use a pulled tag "
        "(llama3.1:8b); for the 'openai' backend use the provider's model id "
        "(e.g. meta-llama/Llama-3.3-70B-Instruct-Turbo on Together).",
    )

    # --- Hosted (OpenAI-compatible) provider -------------------------------
    api_base_url: str = Field(
        default="https://api.together.xyz/v1",
        description="Base URL for the OpenAI-compatible 'openai' backend.",
    )
    api_key: str = Field(
        default="",
        description="API key for the hosted provider (used by the 'openai' backend).",
    )
    embed_api_base_url: str = Field(
        default="",
        description="Optional separate base URL for hosted embeddings; falls back "
        "to api_base_url when empty.",
    )
    embed_api_key: str = Field(
        default="",
        description="Optional separate key for hosted embeddings; falls back to "
        "api_key when empty.",
    )

    # --- Embedding backend -------------------------------------------------
    embed_backend: Literal["ollama", "openai", "hash"] = Field(
        default="ollama",
        description="Embedding backend. 'ollama' uses a local embedding model; "
        "'openai' uses a hosted OpenAI-compatible embeddings endpoint; 'hash' is "
        "a deterministic offline fallback that needs no server.",
    )
    embed_model: str = Field(
        default="nomic-embed-text",
        description="Embedding model. For Ollama: nomic-embed-text. For the "
        "'openai' backend: the provider's id (e.g. BAAI/bge-large-en-v1.5).",
    )
    embed_dim: int = Field(
        default=512,
        description="Dimensionality used by the offline 'hash' embedding backend.",
    )

    # --- Retrieval ---------------------------------------------------------
    top_k: int = Field(default=6, description="Number of chunks retrieved per query.")
    chunk_lines: int = Field(default=60, description="Lines of source per chunk.")
    chunk_overlap: int = Field(default=12, description="Overlapping lines between chunks.")
    max_file_bytes: int = Field(
        default=512_000,
        description="Skip files larger than this many bytes during ingestion.",
    )

    # --- Generation --------------------------------------------------------
    temperature: float = Field(default=0.2, description="Sampling temperature.")
    max_context_chars: int = Field(
        default=12_000,
        description="Character budget for retrieved context in the prompt.",
    )

    # --- Storage -----------------------------------------------------------
    data_dir: Path = Field(
        default=Path.home() / ".aria",
        description="Where Aria stores its index and cloned repositories.",
    )

    @property
    def index_dir(self) -> Path:
        return self.data_dir / "index"

    @property
    def repos_dir(self) -> Path:
        return self.data_dir / "repos"

    @property
    def resolved_embed_api_base_url(self) -> str:
        return self.embed_api_base_url or self.api_base_url

    @property
    def resolved_embed_api_key(self) -> str:
        return self.embed_api_key or self.api_key

    def ensure_dirs(self) -> None:
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.repos_dir.mkdir(parents=True, exist_ok=True)


def load_settings(**overrides) -> AriaSettings:
    """Load settings from the environment, applying any explicit overrides."""
    return AriaSettings(**overrides)
