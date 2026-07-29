from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .agent import AriaAgent
from .config import load_settings
from .ingest import ingest_repo
from .models import AriaError
from .team import TeamJudge, load_catalog

# A single in-process agent (the index is held in memory). Run with
# `uvicorn aria.api:app --workers 1` because the index is not shared across
# worker processes.
_state: dict[str, AriaAgent] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    _state["agent"] = AriaAgent.load(load_settings())
    yield
    _state.clear()


app = FastAPI(
    title="Aria API",
    description="Open-source RAG assistant over GitHub repositories.",
    version="0.1.0",
    lifespan=lifespan,
)


def _agent() -> AriaAgent:
    return _state["agent"]


class IngestRequest(BaseModel):
    source: str


class AskRequest(BaseModel):
    question: str
    top_k: int | None = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "indexed_chunks": len(_agent().store)}


@app.get("/repos")
def repos() -> dict:
    return {"repos": [r.model_dump() for r in _agent().stats()]}


@app.post("/ingest")
def ingest(req: IngestRequest) -> dict:
    agent = _agent()
    try:
        stats = ingest_repo(req.source, agent.settings, agent.store, agent.embedder)
        agent.save()
    except AriaError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return stats.model_dump()


@app.post("/ask")
def ask(req: AskRequest) -> dict:
    agent = _agent()
    if len(agent.store) == 0:
        raise HTTPException(status_code=409, detail="No repositories indexed yet.")
    try:
        if req.top_k:
            agent.settings.top_k = req.top_k
        answer = agent.ask(req.question)
    except AriaError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return answer.model_dump()


@app.get("/team/models")
def team_models() -> dict:
    catalog = load_catalog()
    return {
        "roles": [r.model_dump() for r in catalog.roles],
        "models": [m.model_dump() for m in catalog.models],
    }


@app.get("/team/recommend")
def team_recommend(method: str = "auto", include_noncommercial: bool = False) -> dict:
    if method not in ("auto", "llm", "heuristic"):
        raise HTTPException(status_code=400, detail="method must be auto|llm|heuristic")
    judge = TeamJudge(_agent().llm)
    try:
        roster = judge.recommend(method=method, include_noncommercial=include_noncommercial)
    except AriaError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return roster.model_dump()


@app.delete("/repos/{owner}/{name}")
def remove(owner: str, name: str) -> dict:
    agent = _agent()
    removed = agent.store.delete_repo(f"{owner}/{name}")
    if removed:
        agent.save()
    return {"repo": f"{owner}/{name}", "removed_chunks": removed}
