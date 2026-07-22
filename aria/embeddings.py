from __future__ import annotations

import hashlib
import re
from abc import ABC, abstractmethod

import httpx
import numpy as np

from .config import AriaSettings
from .models import BackendError

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


class EmbeddingBackend(ABC):
    """Turns text into fixed-length vectors used for similarity search."""

    dim: int

    @abstractmethod
    def embed(self, texts: list[str]) -> np.ndarray:
        """Return an ``(len(texts), dim)`` float32 array of unit-norm vectors."""

    def embed_one(self, text: str) -> np.ndarray:
        return self.embed([text])[0]


def _l2_normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (matrix / norms).astype(np.float32)


class HashEmbedding(EmbeddingBackend):
    """Deterministic, dependency-free embedding for offline use and tests.

    Tokens are hashed into a fixed number of buckets (the "hashing trick") and
    the resulting bag-of-tokens vector is L2-normalized. It is not
    state-of-the-art, but it is real, reproducible, and needs no network — which
    makes Aria fully runnable and testable without any model server.
    """

    def __init__(self, dim: int = 512) -> None:
        self.dim = dim

    def embed(self, texts: list[str]) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, text in enumerate(texts):
            for tok in _TOKEN_RE.findall(text.lower()):
                h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
                bucket = h % self.dim
                sign = 1.0 if (h >> 8) & 1 else -1.0
                out[i, bucket] += sign
        return _l2_normalize(out)


class OllamaEmbedding(EmbeddingBackend):
    """Embeddings from a local Ollama server (e.g. ``nomic-embed-text``)."""

    def __init__(self, host: str, model: str, timeout: float = 60.0) -> None:
        self.host = host.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._dim: int | None = None

    @property
    def dim(self) -> int:  # type: ignore[override]
        if self._dim is None:
            self._dim = int(self.embed_one("dimension probe").shape[0])
        return self._dim

    @dim.setter
    def dim(self, value: int) -> None:
        self._dim = value

    def embed(self, texts: list[str]) -> np.ndarray:
        vectors: list[list[float]] = []
        try:
            with httpx.Client(timeout=self.timeout) as client:
                for text in texts:
                    resp = client.post(
                        f"{self.host}/api/embeddings",
                        json={"model": self.model, "prompt": text},
                    )
                    resp.raise_for_status()
                    vectors.append(resp.json()["embedding"])
        except (httpx.HTTPError, KeyError) as e:
            raise BackendError(
                f"Ollama embedding request failed ({e}). Is Ollama running at "
                f"{self.host} with model '{self.model}' pulled?"
            ) from e
        return _l2_normalize(np.asarray(vectors, dtype=np.float32))


def make_embedding_backend(settings: AriaSettings) -> EmbeddingBackend:
    if settings.embed_backend == "hash":
        return HashEmbedding(dim=settings.embed_dim)
    return OllamaEmbedding(host=settings.ollama_host, model=settings.embed_model)
