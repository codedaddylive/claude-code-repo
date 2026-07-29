from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import numpy as np

from .models import Chunk, RepoStats, SearchResult


class VectorStore:
    """A minimal, persistent vector store backed by NumPy.

    Vectors live in a single ``(n, dim)`` matrix; chunk metadata lives in a
    parallel list. Similarity is cosine (vectors are stored unit-normalized, so
    a dot product suffices). This is intentionally dependency-light — no FAISS,
    no external database — which keeps Aria easy to run anywhere. For very large
    corpora, swap this class for an ANN index behind the same interface.
    """

    def __init__(self, dim: int) -> None:
        self.dim = dim
        self._vectors = np.zeros((0, dim), dtype=np.float32)
        self._chunks: list[Chunk] = []

    def __len__(self) -> int:
        return len(self._chunks)

    def add(self, chunks: list[Chunk], vectors: np.ndarray) -> None:
        if len(chunks) == 0:
            return
        if vectors.shape[1] != self.dim:
            raise ValueError(
                f"Vector dim {vectors.shape[1]} does not match store dim {self.dim}"
            )
        self._vectors = np.vstack([self._vectors, vectors.astype(np.float32)])
        self._chunks.extend(chunks)

    def search(self, query_vec: np.ndarray, top_k: int = 6) -> list[SearchResult]:
        if len(self._chunks) == 0:
            return []
        scores = self._vectors @ query_vec.astype(np.float32)
        k = min(top_k, len(scores))
        # argpartition for the top-k, then sort just those by score desc.
        top_idx = np.argpartition(-scores, k - 1)[:k]
        top_idx = top_idx[np.argsort(-scores[top_idx])]
        return [
            SearchResult(chunk=self._chunks[i], score=float(scores[i])) for i in top_idx
        ]

    def delete_repo(self, repo: str) -> int:
        keep = [i for i, c in enumerate(self._chunks) if c.repo != repo]
        removed = len(self._chunks) - len(keep)
        if removed:
            self._vectors = self._vectors[keep]
            self._chunks = [self._chunks[i] for i in keep]
        return removed

    def stats(self) -> list[RepoStats]:
        files: dict[str, set[str]] = defaultdict(set)
        counts: dict[str, int] = defaultdict(int)
        for c in self._chunks:
            files[c.repo].add(c.path)
            counts[c.repo] += 1
        return [
            RepoStats(repo=repo, files=len(files[repo]), chunks=counts[repo])
            for repo in sorted(counts)
        ]

    # --- persistence -------------------------------------------------------
    def save(self, index_dir: Path) -> None:
        index_dir.mkdir(parents=True, exist_ok=True)
        np.save(index_dir / "vectors.npy", self._vectors)
        with (index_dir / "chunks.jsonl").open("w", encoding="utf-8") as f:
            for chunk in self._chunks:
                f.write(chunk.model_dump_json() + "\n")
        (index_dir / "meta.txt").write_text(str(self.dim), encoding="utf-8")

    @classmethod
    def load(cls, index_dir: Path, dim: int) -> "VectorStore":
        store = cls(dim=dim)
        vec_path = index_dir / "vectors.npy"
        chunk_path = index_dir / "chunks.jsonl"
        if not vec_path.exists() or not chunk_path.exists():
            return store
        vectors = np.load(vec_path)
        chunks = [
            Chunk.model_validate_json(line)
            for line in chunk_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if vectors.shape[0] != len(chunks):
            raise ValueError("Corrupt index: vector/chunk count mismatch")
        if vectors.shape[0] and vectors.shape[1] != dim:
            store.dim = vectors.shape[1]
        store._vectors = vectors.astype(np.float32)
        store._chunks = chunks
        return store
