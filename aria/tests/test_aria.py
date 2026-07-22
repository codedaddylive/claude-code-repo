"""Offline test suite for Aria.

Everything here runs without a model server by using the deterministic 'hash'
embedding backend and the 'echo' LLM backend. Run with:

    python -m aria.tests.test_aria      # plain, no pytest required
    pytest aria/tests/test_aria.py      # or via pytest
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from aria.agent import AriaAgent
from aria.config import load_settings
from aria.embeddings import HashEmbedding, make_embedding_backend
from aria.ingest import chunk_file, ingest_repo, normalize_repo
from aria.llm import EchoLLM, make_llm_backend
from aria.models import Chunk
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
