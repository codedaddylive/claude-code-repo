from __future__ import annotations

from pydantic import BaseModel, Field


class Chunk(BaseModel):
    """A contiguous slice of a source file, the unit Aria retrieves over."""

    id: str
    repo: str
    path: str
    start_line: int
    end_line: int
    text: str

    @property
    def citation(self) -> str:
        return f"{self.repo}/{self.path}:{self.start_line}-{self.end_line}"


class SearchResult(BaseModel):
    """A chunk paired with its similarity score for a given query."""

    chunk: Chunk
    score: float


class ChatMessage(BaseModel):
    role: str  # "system" | "user" | "assistant"
    content: str


class Answer(BaseModel):
    """The result of asking Aria a question."""

    question: str
    answer: str
    sources: list[SearchResult] = Field(default_factory=list)


class RepoStats(BaseModel):
    """Summary of what has been ingested for a repository."""

    repo: str
    files: int = 0
    chunks: int = 0


class AriaError(Exception):
    """Base class for Aria-specific errors."""


class IngestError(AriaError):
    pass


class BackendError(AriaError):
    pass
