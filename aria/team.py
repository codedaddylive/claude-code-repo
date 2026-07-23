from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from .llm import LLMBackend
from .models import AriaError, ChatMessage

_DATA_FILE = Path(__file__).parent / "data" / "models.json"


# --------------------------------------------------------------------------- #
# Catalog models
# --------------------------------------------------------------------------- #
class Role(BaseModel):
    id: str
    name: str
    description: str
    modality: Literal["text", "image"] = "text"


class ModelCard(BaseModel):
    id: str
    name: str
    provider: str
    modality: Literal["text", "image"] = "text"
    license: str
    open_weights: bool = True
    free_commercial_use: Literal["yes", "limited", "no"] = "yes"
    params: str = ""
    run: str = ""
    homepage: str = ""
    strengths: list[str] = Field(default_factory=list)
    role_affinity: dict[str, int] = Field(default_factory=dict)


class Catalog(BaseModel):
    roles: list[Role]
    models: list[ModelCard]

    def role(self, role_id: str) -> Role:
        for r in self.roles:
            if r.id == role_id:
                return r
        raise AriaError(f"Unknown role: {role_id}")


def load_catalog(path: Path | None = None) -> Catalog:
    raw = json.loads((path or _DATA_FILE).read_text(encoding="utf-8"))
    return Catalog(roles=raw["roles"], models=raw["models"])


# --------------------------------------------------------------------------- #
# Judge output models
# --------------------------------------------------------------------------- #
class Candidate(BaseModel):
    model_id: str
    name: str
    score: float
    reason: str = ""


class RolePick(BaseModel):
    role_id: str
    role_name: str
    winner_id: str
    winner_name: str
    score: float
    reason: str
    runners_up: list[Candidate] = Field(default_factory=list)


class TeamRoster(BaseModel):
    method: str  # "llm" | "heuristic"
    picks: list[RolePick]


# --------------------------------------------------------------------------- #
# Judge
# --------------------------------------------------------------------------- #
JUDGE_SYSTEM = (
    "You are Aria's model-selection judge. You choose the best FREE, OPEN-SOURCE "
    "model for a given role. Prefer permissive licenses (MIT/Apache) and models "
    "that are genuinely free to run. Judge on the role's needs and each model's "
    "stated strengths. Respond with JSON only — no prose."
)


def parse_judge_scores(text: str) -> list[dict]:
    """Extract a ``[{id, score, reason}]`` array from a judge reply.

    Tolerant of models that wrap JSON in prose or code fences: it grabs the
    first top-level ``[...]`` block and parses it. Returns ``[]`` if none is
    found or it does not parse.
    """
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        return []
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    out = []
    for item in data:
        if isinstance(item, dict) and "id" in item and "score" in item:
            out.append(item)
    return out


class TeamJudge:
    """Assembles a role→model team from the open-source catalog.

    Two scoring modes:
    * ``llm`` — Aria's own LLM scores each candidate per role (LLM-as-a-judge).
    * ``heuristic`` — deterministic scoring from the catalog's ``role_affinity``
      (used offline / as a fallback, and to keep the pipeline testable).
    """

    def __init__(self, llm: LLMBackend, catalog: Catalog | None = None) -> None:
        self.llm = llm
        self.catalog = catalog or load_catalog()

    def candidates_for(self, role: Role, include_noncommercial: bool = False) -> list[ModelCard]:
        out = []
        for m in self.catalog.models:
            if m.modality != role.modality or not m.open_weights:
                continue
            if m.free_commercial_use == "no" and not include_noncommercial:
                continue
            out.append(m)
        return out

    # --- heuristic scoring --------------------------------------------------
    def _score_heuristic(self, role: Role, cards: list[ModelCard]) -> list[Candidate]:
        scored = []
        for c in cards:
            affinity = c.role_affinity.get(role.id, 0)  # 1..5
            penalty = 0.5 if c.free_commercial_use == "limited" else 0.0
            score = round(max(0.0, affinity * 2.0 - penalty), 2)  # → 0..10
            reason = (
                f"affinity {affinity}/5 for {role.name}"
                + (f"; strengths: {', '.join(c.strengths[:3])}" if c.strengths else "")
                + (" (license limits commercial use)" if penalty else "")
            )
            scored.append(Candidate(model_id=c.id, name=c.name, score=score, reason=reason))
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored

    # --- LLM scoring --------------------------------------------------------
    def _score_llm(self, role: Role, cards: list[ModelCard]) -> list[Candidate]:
        payload = [
            {
                "id": c.id, "name": c.name, "license": c.license,
                "free_commercial_use": c.free_commercial_use,
                "params": c.params, "strengths": c.strengths,
            }
            for c in cards
        ]
        prompt = (
            f"Role: {role.name}\nWhat it does: {role.description}\n\n"
            f"Candidate open-source models (JSON):\n{json.dumps(payload, indent=2)}\n\n"
            "Score EACH candidate 0-10 for how well it fits THIS role. Reward free, "
            "permissively-licensed models. Return ONLY a JSON array of objects with "
            'keys "id", "score" (number), and "reason" (one short sentence).'
        )
        reply = self.llm.chat(
            [ChatMessage(role="system", content=JUDGE_SYSTEM),
             ChatMessage(role="user", content=prompt)],
            temperature=0.0,
        )
        raw = parse_judge_scores(reply)
        if not raw:
            return []  # no usable scores → caller falls back to heuristic
        by_id = {r["id"]: r for r in raw}
        # Map judge scores back onto candidates; any candidate the judge omitted
        # falls back to its heuristic score so a partial reply still ranks fully.
        heuristic = {c.model_id: c for c in self._score_heuristic(role, cards)}
        scored: list[Candidate] = []
        for c in cards:
            if c.id in by_id:
                try:
                    score = float(by_id[c.id]["score"])
                except (TypeError, ValueError):
                    score = heuristic[c.id].score
                reason = str(by_id[c.id].get("reason", "")) or heuristic[c.id].reason
                scored.append(Candidate(model_id=c.id, name=c.name,
                                        score=round(score, 2), reason=reason))
            else:
                scored.append(heuristic[c.id])
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored

    # --- top-level ----------------------------------------------------------
    def recommend(
        self,
        method: Literal["auto", "llm", "heuristic"] = "auto",
        include_noncommercial: bool = False,
    ) -> TeamRoster:
        # 'auto' uses the LLM but falls back to heuristic per-role if the reply
        # can't be parsed (e.g. the offline echo backend).
        use_llm = method in ("auto", "llm")
        picks: list[RolePick] = []
        effective = "heuristic"
        for role in self.catalog.roles:
            cards = self.candidates_for(role, include_noncommercial)
            if not cards:
                continue
            scored: list[Candidate] = []
            if use_llm and method != "heuristic":
                try:
                    scored = self._score_llm(role, cards)
                except AriaError:
                    scored = []
                if scored:
                    effective = "llm"  # the judge produced real scores this role
            if not scored:
                scored = self._score_heuristic(role, cards)
            winner = scored[0]
            picks.append(
                RolePick(
                    role_id=role.id, role_name=role.name,
                    winner_id=winner.model_id, winner_name=winner.name,
                    score=winner.score, reason=winner.reason,
                    runners_up=scored[1:3],
                )
            )
        return TeamRoster(method=(effective if method != "heuristic" else "heuristic"),
                          picks=picks)
