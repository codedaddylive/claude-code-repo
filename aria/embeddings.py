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
    def embed(self, texts: list[str], input_type: str | None = None) -> np.ndarray:
        """Return an ``(len(texts), dim)`` float32 array of unit-norm vectors.

        ``input_type`` ("query" | "passage") is a hint some providers (notably
        NVIDIA NIM) require for asymmetric retrieval models; most backends
        ignore it. Aria passes "passage" when indexing and "query" when searching.
        """

    def embed_one(self, text: str, input_type: str | None = None) -> np.ndarray:
        return self.embed([text], input_type=input_type)[0]


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

    def embed(self, texts: list[str], input_type: str | None = None) -> np.ndarray:
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

    def embed(self, texts: list[str], input_type: str | None = None) -> np.ndarray:
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


def parse_openai_embeddings(data: dict) -> list[list[float]]:
    """Extract vectors from an OpenAI-style embeddings response."""
    return [item["embedding"] for item in data["data"]]


class OpenAICompatEmbedding(EmbeddingBackend):
    """Embeddings from any OpenAI-compatible hosted provider (e.g. Together).

    Set ``nvidia_style=True`` for NVIDIA NIM embedding models, which require an
    ``input_type`` ("query"/"passage") and a ``truncate`` field beyond the plain
    OpenAI schema.
    """

    def __init__(self, base_url: str, api_key: str, model: str, timeout: float = 60.0,
                 nvidia_style: bool = False) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.nvidia_style = nvidia_style
        self._dim: int | None = None

    def _build_body(self, texts: list[str], input_type: str | None) -> dict:
        body: dict = {"model": self.model, "input": texts}
        if self.nvidia_style:
            body["input_type"] = input_type or "passage"
            body["truncate"] = "END"
        return body

    @property
    def dim(self) -> int:  # type: ignore[override]
        if self._dim is None:
            self._dim = int(self.embed_one("dimension probe").shape[0])
        return self._dim

    @dim.setter
    def dim(self, value: int) -> None:
        self._dim = value

    def embed(self, texts: list[str], input_type: str | None = None) -> np.ndarray:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    f"{self.base_url}/embeddings",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=self._build_body(texts, input_type),
                )
                resp.raise_for_status()
                vectors = parse_openai_embeddings(resp.json())
        except (httpx.HTTPError, KeyError, IndexError) as e:
            raise BackendError(
                f"Hosted embedding request to {self.base_url} failed ({e}). Check "
                f"ARIA_API_KEY and that embed model '{self.model}' is valid."
            ) from e
        return _l2_normalize(np.asarray(vectors, dtype=np.float32))


def make_embedding_backend(settings: AriaSettings) -> EmbeddingBackend:
    if settings.embed_backend == "hash":
        return HashEmbedding(dim=settings.embed_dim)
    if settings.embed_backend == "openai":
        key = settings.resolved_embed_api_key
        if not key:
            raise BackendError(
                "ARIA_EMBED_BACKEND=openai requires ARIA_API_KEY (or "
                "ARIA_EMBED_API_KEY) to be set."
            )
        return OpenAICompatEmbedding(
            base_url=settings.resolved_embed_api_base_url,
            api_key=key,
            model=settings.embed_model,
            nvidia_style=(settings.embed_provider_style == "nvidia"),
        )
    return OllamaEmbedding(host=settings.ollama_host, model=settings.embed_model)
