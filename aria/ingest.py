from __future__ import annotations

import hashlib
import subprocess
from collections.abc import Iterable
from pathlib import Path

from .config import AriaSettings
from .embeddings import EmbeddingBackend
from .models import Chunk, IngestError, RepoStats
from .vectorstore import VectorStore

# Directories that never contain useful source to index.
SKIP_DIRS = {
    ".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build",
    ".mypy_cache", ".pytest_cache", ".idea", ".vscode", "target", "vendor",
    ".next", ".cache", "site-packages",
}

# Extensions worth indexing (source, config, and docs).
TEXT_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".kt", ".rb",
    ".c", ".h", ".cpp", ".hpp", ".cc", ".cs", ".php", ".swift", ".scala", ".sh",
    ".bash", ".zsh", ".sql", ".r", ".jl", ".lua", ".pl", ".ex", ".exs", ".clj",
    ".md", ".mdx", ".rst", ".txt", ".toml", ".yaml", ".yml", ".json", ".ini",
    ".cfg", ".env", ".dockerfile", ".tf", ".gradle", ".proto", ".html", ".css",
}
# Files worth indexing regardless of extension.
TEXT_FILENAMES = {"Dockerfile", "Makefile", "README", "LICENSE", ".gitignore"}


def normalize_repo(source: str) -> tuple[str, str]:
    """Return ``(clone_url, repo_name)`` for a GitHub URL, shorthand, or path.

    Accepts ``https://github.com/owner/repo``, ``owner/repo``,
    ``git@github.com:owner/repo.git``, or a local directory path.
    """
    source = source.strip()
    if Path(source).is_dir():
        name = Path(source).resolve().name
        return source, name
    if source.startswith(("http://", "https://", "git@")):
        url = source
        # Normalize the SSH form (git@host:owner/repo) so the separator between
        # host and path is a slash, then take the last two path components.
        path = source.rstrip("/").replace(":", "/")
        tail = path.split("/")[-2:]
        name = "/".join(tail).removesuffix(".git")
    elif source.count("/") == 1 and " " not in source:
        url = f"https://github.com/{source}.git"
        name = source
    else:
        raise IngestError(f"Unrecognized repository source: {source!r}")
    return url, name.removesuffix(".git")


def clone_repo(source: str, dest_root: Path) -> tuple[Path, str]:
    """Shallow-clone ``source`` into ``dest_root``; return ``(path, repo_name)``.

    A local directory source is used in place (not copied).
    """
    url, name = normalize_repo(source)
    if Path(source).is_dir():
        return Path(source).resolve(), name

    dest = dest_root / name.replace("/", "__")
    if dest.exists():
        # Refresh an existing clone rather than failing.
        try:
            subprocess.run(
                ["git", "-C", str(dest), "pull", "--ff-only", "--depth", "1"],
                check=True, capture_output=True, text=True,
            )
            return dest, name
        except subprocess.CalledProcessError:
            pass  # fall through to a fresh clone
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", url, str(dest)],
            check=True, capture_output=True, text=True,
        )
    except FileNotFoundError as e:
        raise IngestError("git is not installed or not on PATH.") from e
    except subprocess.CalledProcessError as e:
        raise IngestError(f"git clone failed for {url}:\n{e.stderr.strip()}") from e
    return dest, name


def _is_text_file(path: Path, max_bytes: int) -> bool:
    if path.name in TEXT_FILENAMES:
        return True
    if path.suffix.lower() not in TEXT_EXTENSIONS:
        return False
    try:
        if path.stat().st_size > max_bytes:
            return False
    except OSError:
        return False
    return True


def iter_source_files(root: Path, max_bytes: int) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        if _is_text_file(path, max_bytes):
            yield path


def chunk_file(
    repo: str, rel_path: str, text: str, chunk_lines: int, overlap: int
) -> list[Chunk]:
    lines = text.splitlines()
    if not lines:
        return []
    step = max(1, chunk_lines - overlap)
    chunks: list[Chunk] = []
    for start in range(0, len(lines), step):
        window = lines[start : start + chunk_lines]
        body = "\n".join(window).strip()
        if not body:
            if start + chunk_lines >= len(lines):
                break
            continue
        start_line = start + 1
        end_line = start + len(window)
        cid = hashlib.md5(f"{repo}:{rel_path}:{start_line}".encode()).hexdigest()[:16]
        chunks.append(
            Chunk(
                id=cid, repo=repo, path=rel_path,
                start_line=start_line, end_line=end_line, text=body,
            )
        )
        if start + chunk_lines >= len(lines):
            break
    return chunks


def ingest_repo(
    source: str,
    settings: AriaSettings,
    store: VectorStore,
    embedder: EmbeddingBackend,
    on_progress=None,
) -> RepoStats:
    """Clone, chunk, embed, and index a repository into ``store``.

    Re-ingesting a repo replaces its previously indexed content.
    """
    settings.ensure_dirs()
    repo_path, repo_name = clone_repo(source, settings.repos_dir)

    store.delete_repo(repo_name)  # idempotent re-ingest

    files = list(iter_source_files(repo_path, settings.max_file_bytes))
    all_chunks: list[Chunk] = []
    for i, path in enumerate(files):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        rel = str(path.relative_to(repo_path))
        all_chunks.extend(
            chunk_file(repo_name, rel, text, settings.chunk_lines, settings.chunk_overlap)
        )
        if on_progress:
            on_progress(i + 1, len(files), rel)

    if all_chunks:
        vectors = embedder.embed([c.text for c in all_chunks], input_type="passage")
        store.add(all_chunks, vectors)

    return RepoStats(repo=repo_name, files=len(files), chunks=len(all_chunks))
