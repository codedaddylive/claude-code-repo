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
    llm_backend: Literal["ollama", "echo"] = Field(
        default="ollama",
        description="Which LLM backend to use. 'ollama' talks to a local Ollama "
        "server; 'echo' is an offline stub used for tests and demos.",
    )
    ollama_host: str = Field(
        default="http://localhost:11434",
        description="Base URL of the Ollama server.",
    )
    model: str = Field(
        default="llama3.1:8b",
        description="Open-source chat model served by Ollama.",
    )

    # --- Embedding backend -------------------------------------------------
    embed_backend: Literal["ollama", "hash"] = Field(
        default="ollama",
        description="Embedding backend. 'ollama' uses a local embedding model; "
        "'hash' is a deterministic offline fallback that needs no server.",
    )
    embed_model: str = Field(
        default="nomic-embed-text",
        description="Open-source embedding model served by Ollama.",
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

    def ensure_dirs(self) -> None:
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.repos_dir.mkdir(parents=True, exist_ok=True)


def load_settings(**overrides) -> AriaSettings:
    """Load settings from the environment, applying any explicit overrides."""
    return AriaSettings(**overrides)
