"""Offline test suite for Aria.

Everything here runs without a model server by using the deterministic 'hash'
embedding backend and the 'echo' LLM backend. Run with:

    python -m aria.tests.test_aria      # plain, no pytest required
    pytest aria/tests/test_aria.py      # or via pytest
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from aria.agent import AriaAgent
from aria.config import load_settings
from aria.embeddings import (
    HashEmbedding,
    OpenAICompatEmbedding,
    make_embedding_backend,
    parse_openai_embeddings,
)
from aria.ingest import chunk_file, ingest_repo, normalize_repo
from aria.llm import (
    EchoLLM,
    OpenAICompatLLM,
    make_llm_backend,
    parse_openai_chat,
    parse_openai_stream_line,
)
from aria.llm import LLMBackend
from aria.models import BackendError, Chunk
from aria.team import TeamJudge, load_catalog, parse_judge_scores
from aria.vectorstore import VectorStore


def _offline_settings(data_dir: Path):
    return load_settings(
        llm_backend="echo",
        embed_backend="hash",
        embed_dim=256,
        data_dir=data_dir,
        chunk_lines=20,
        chunk_overlap=5,
    )


def test_normalize_repo_forms():
    assert normalize_repo("owner/repo") == ("https://github.com/owner/repo.git", "owner/repo")
    url, name = normalize_repo("https://github.com/foo/bar")
    assert url == "https://github.com/foo/bar" and name == "foo/bar"
    url, name = normalize_repo("git@github.com:foo/bar.git")
    assert name == "foo/bar"


def test_hash_embedding_is_deterministic_and_normalized():
    emb = HashEmbedding(dim=128)
    a = emb.embed(["def hello(): return 1"])
    b = emb.embed(["def hello(): return 1"])
    assert a.shape == (1, 128)
    assert (a == b).all()  # deterministic
    assert abs(float((a[0] ** 2).sum()) - 1.0) < 1e-5  # unit norm


def test_chunk_file_line_ranges_and_overlap():
    text = "\n".join(f"line {i}" for i in range(1, 51))
    chunks = chunk_file("r", "f.py", text, chunk_lines=20, overlap=5)
    assert chunks[0].start_line == 1 and chunks[0].end_line == 20
    # step = chunk_lines - overlap = 15, so the second chunk starts at line 16.
    assert chunks[1].start_line == 16
    assert all(isinstance(c, Chunk) for c in chunks)
    assert chunks[-1].end_line == 50


def test_vectorstore_search_and_persistence():
    emb = HashEmbedding(dim=256)
    store = VectorStore(dim=256)
    chunks = [
        Chunk(id="1", repo="r", path="auth.py", start_line=1, end_line=3,
              text="def login(user, password): verify credentials and issue a token"),
        Chunk(id="2", repo="r", path="math.py", start_line=1, end_line=3,
              text="def add(a, b): return a plus b arithmetic sum"),
    ]
    store.add(chunks, emb.embed([c.text for c in chunks]))

    results = store.search(emb.embed_one("how does user login and password work"), top_k=2)
    assert results[0].chunk.path == "auth.py"  # most relevant first

    with tempfile.TemporaryDirectory() as d:
        idx = Path(d) / "index"
        store.save(idx)
        reloaded = VectorStore.load(idx, dim=256)
        assert len(reloaded) == 2
        r2 = reloaded.search(emb.embed_one("password login token"), top_k=1)
        assert r2[0].chunk.path == "auth.py"


def test_vectorstore_delete_repo_and_stats():
    emb = HashEmbedding(dim=64)
    store = VectorStore(dim=64)
    store.add(
        [Chunk(id="a", repo="x/one", path="a.py", start_line=1, end_line=1, text="alpha"),
         Chunk(id="b", repo="x/two", path="b.py", start_line=1, end_line=1, text="beta")],
        emb.embed(["alpha", "beta"]),
    )
    assert {s.repo for s in store.stats()} == {"x/one", "x/two"}
    assert store.delete_repo("x/one") == 1
    assert [s.repo for s in store.stats()] == ["x/two"]


def test_end_to_end_ingest_and_ask_offline():
    with tempfile.TemporaryDirectory() as d:
        data_dir = Path(d) / "aria"
        repo = Path(d) / "sample-repo"
        (repo / "src").mkdir(parents=True)
        (repo / "src" / "auth.py").write_text(
            "def login(username, password):\n"
            "    '''Authenticate a user and return a session token.'''\n"
            "    return issue_token(username)\n"
        )
        (repo / "README.md").write_text("# Sample\nThis project handles user login.\n")

        settings = _offline_settings(data_dir)
        embedder = make_embedding_backend(settings)
        store = VectorStore(dim=embedder.dim)
        stats = ingest_repo(str(repo), settings, store, embedder)
        assert stats.files == 2
        assert stats.chunks >= 2

        agent = AriaAgent(settings, store, embedder, make_llm_backend(settings))
        answer = agent.ask("how does login work?")
        assert answer.sources, "expected retrieved sources"
        # The offline hash embedding is crude; assert auth.py is retrieved,
        # not that it ranks first.
        assert any("auth.py" in s.chunk.citation for s in answer.sources)
        assert isinstance(agent.llm, EchoLLM)
        # Echo backend surfaces the question in its reply.
        assert "login" in answer.answer.lower()


def test_agent_load_roundtrip_persists_index():
    with tempfile.TemporaryDirectory() as d:
        data_dir = Path(d) / "aria"
        repo = Path(d) / "r"
        repo.mkdir()
        (repo / "main.py").write_text("print('hello world')\n")

        settings = _offline_settings(data_dir)
        agent = AriaAgent.load(settings)
        ingest_repo(str(repo), settings, agent.store, agent.embedder)
        agent.save()

        reloaded = AriaAgent.load(settings)
        assert len(reloaded.store) >= 1


def test_chunk_citation_is_serialized():
    c = Chunk(id="1", repo="o/r", path="a.py", start_line=3, end_line=9, text="x")
    dumped = c.model_dump()
    assert dumped["citation"] == "o/r/a.py:3-9"  # API consumers get it directly
    # ...and a chunk containing the computed field still validates on reload.
    assert Chunk.model_validate_json(c.model_dump_json()).citation == "o/r/a.py:3-9"


def test_openai_response_parsers():
    chat = {"choices": [{"message": {"role": "assistant", "content": "hello there"}}]}
    assert parse_openai_chat(chat) == "hello there"

    emb = {"data": [{"embedding": [0.1, 0.2]}, {"embedding": [0.3, 0.4]}]}
    assert parse_openai_embeddings(emb) == [[0.1, 0.2], [0.3, 0.4]]

    # Streaming SSE lines.
    delta = 'data: {"choices":[{"delta":{"content":"Hi"}}]}'
    assert parse_openai_stream_line(delta) == "Hi"
    assert parse_openai_stream_line("data: [DONE]") is None
    assert parse_openai_stream_line("") is None
    assert parse_openai_stream_line(": keep-alive") is None


def test_backend_factory_selection_and_key_validation():
    # 'openai' backends select the OpenAI-compatible classes when a key is set.
    s = load_settings(
        llm_backend="openai", embed_backend="openai",
        api_key="test-key", model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
        embed_model="BAAI/bge-large-en-v1.5",
    )
    assert isinstance(make_llm_backend(s), OpenAICompatLLM)
    assert isinstance(make_embedding_backend(s), OpenAICompatEmbedding)

    # Missing key is a clear, early error (no silent misconfiguration).
    s_nokey = load_settings(llm_backend="openai", embed_backend="openai", api_key="")
    for factory in (make_llm_backend, make_embedding_backend):
        try:
            factory(s_nokey)
            raise AssertionError("expected BackendError for missing api_key")
        except BackendError:
            pass


def test_embed_api_credential_fallback():
    s = load_settings(api_base_url="https://chat.example/v1", api_key="shared")
    assert s.resolved_embed_api_base_url == "https://chat.example/v1"
    assert s.resolved_embed_api_key == "shared"
    s2 = load_settings(
        api_key="shared",
        embed_api_base_url="https://embed.example/v1",
        embed_api_key="embed-only",
    )
    assert s2.resolved_embed_api_base_url == "https://embed.example/v1"
    assert s2.resolved_embed_api_key == "embed-only"


def test_catalog_loads_and_is_consistent():
    cat = load_catalog()
    assert len(cat.models) >= 10
    valid_roles = {r.id for r in cat.roles}
    # Every affinity key references a real role; there is at least one image model.
    for m in cat.models:
        assert set(m.role_affinity).issubset(valid_roles), m.id
        assert m.free_commercial_use in {"yes", "limited", "no"}
    assert any(m.modality == "image" for m in cat.models)
    assert "designer" in valid_roles


def test_parse_judge_scores_tolerates_prose_and_fences():
    good = '[{"id":"a","score":9,"reason":"x"},{"id":"b","score":4,"reason":"y"}]'
    assert parse_judge_scores(good)[0]["id"] == "a"
    fenced = 'Here you go:\n```json\n[{"id":"a","score":7}]\n```\nthanks!'
    assert parse_judge_scores(fenced) == [{"id": "a", "score": 7}]
    assert parse_judge_scores("no json here") == []
    # Items missing required keys are dropped.
    assert parse_judge_scores('[{"id":"a"},{"score":5}]') == []


def test_team_heuristic_recommend_is_sane_and_deterministic():
    judge = TeamJudge(EchoLLM())  # echo can't produce JSON → forces heuristic
    roster = judge.recommend(method="heuristic")
    assert roster.method == "heuristic"
    picks = {p.role_id: p for p in roster.picks}
    # Every role got a pick and a positive score.
    assert set(picks) == {r.id for r in load_catalog().roles}
    assert all(p.score > 0 for p in roster.picks)
    # Designer must be an image model; reasoning pick should be a known reasoner.
    designer_winner = picks["designer"].winner_id
    image_ids = {m.id for m in load_catalog().models if m.modality == "image"}
    assert designer_winner in image_ids
    assert picks["reasoning"].winner_id in {"deepseek-r1", "qwq-32b"}
    # Deterministic across runs.
    assert judge.recommend(method="heuristic").model_dump() == roster.model_dump()


def test_team_auto_falls_back_to_heuristic_with_echo_backend():
    roster = TeamJudge(EchoLLM()).recommend(method="auto")
    assert roster.method == "heuristic"  # echo reply can't be parsed as scores


class _FakeJudgeLLM(LLMBackend):
    """Scores a target id top and explicitly down-ranks the heuristic leaders,
    so the judge's decision — not the catalog affinities — drives selection."""

    def __init__(self, target_id: str, downrank: list[str]) -> None:
        self.target_id = target_id
        self.downrank = downrank

    def chat(self, messages, *, temperature=0.2) -> str:
        items = [{"id": self.target_id, "score": 10, "reason": "fake judge favors it"}]
        items += [{"id": d, "score": 1, "reason": "downranked"} for d in self.downrank]
        return json.dumps(items)


def test_team_llm_judge_overrides_heuristic():
    # Heuristic would tie several models at 10 for general coding. The judge
    # promotes qwen2.5-coder and demotes the other leaders, so it must win —
    # proving the LLM's scores, not the affinities, decide the pick.
    judge = TeamJudge(_FakeJudgeLLM("qwen25-coder-32b",
                                    downrank=["deepseek-v3", "kimi-k2", "glm-4.5"]))
    roster = judge.recommend(method="llm")
    assert roster.method == "llm"
    picks = {p.role_id: p for p in roster.picks}
    assert picks["general_coding"].winner_id == "qwen25-coder-32b"
    assert picks["general_coding"].score == 10.0
    # A text-only favorite never leaks into the image-only designer role.
    image_ids = {m.id for m in load_catalog().models if m.modality == "image"}
    assert picks["designer"].winner_id in image_ids


def test_noncommercial_models_excluded_by_default():
    judge = TeamJudge(EchoLLM())
    role = load_catalog().role("designer")
    default_ids = {c.id for c in judge.candidates_for(role)}
    assert "flux1-dev" not in default_ids  # non-commercial license filtered out
    with_nc = {c.id for c in judge.candidates_for(role, include_noncommercial=True)}
    assert "flux1-dev" in with_nc


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
        except Exception as e:  # noqa: BLE001
            failures += 1
            print(f"  FAIL  {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    return failures


if __name__ == "__main__":
    import sys

    sys.exit(1 if _run_all() else 0)
