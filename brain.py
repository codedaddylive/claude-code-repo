#!/usr/bin/env python3
"""Knowledge base CLI — add, list, search, and show brain entries."""

import re
import sys
from datetime import date
from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

app = typer.Typer(help="Manage the project knowledge base (brain).")
console = Console()

KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"
CATEGORIES = ["patterns", "apis", "architecture", "domain"]


def _all_entries() -> list[Path]:
    return sorted(KNOWLEDGE_DIR.rglob("*.md"))


def _parse_frontmatter(path: Path) -> dict:
    text = path.read_text()
    meta = {"title": path.stem, "tags": [], "category": path.parent.name}
    if not text.startswith("---"):
        return meta
    end = text.index("---", 3)
    for line in text[3:end].strip().splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            if key == "tags":
                meta["tags"] = [t.strip(" []") for t in val.split(",") if t.strip(" []")]
            else:
                meta[key] = val
    return meta


@app.command()
def add(
    title: str = typer.Option(..., "--title", "-t", prompt=True, help="Entry title"),
    category: str = typer.Option(..., "--category", "-c", prompt=True,
                                  help=f"Category: {', '.join(CATEGORIES)}"),
    tags: str = typer.Option("", "--tags", help="Comma-separated tags"),
    content: str = typer.Option(None, "--content", help="Entry body (omit to open $EDITOR)"),
):
    """Add a new knowledge entry."""
    if category not in CATEGORIES:
        console.print(f"[red]Unknown category '{category}'. Choose from: {', '.join(CATEGORIES)}[/red]")
        raise typer.Exit(1)

    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    target = KNOWLEDGE_DIR / category / f"{slug}.md"
    if target.exists():
        console.print(f"[yellow]Entry already exists: {target.relative_to(Path.cwd())}[/yellow]")
        raise typer.Exit(1)

    tag_list = ", ".join(t.strip() for t in tags.split(",") if t.strip())
    today = date.today().isoformat()

    if content is None:
        content = typer.edit(
            f"---\ntitle: {title}\ncategory: {category}\ntags: [{tag_list}]\ncreated: {today}\n---\n\n# {title}\n\n"
        )
        if not content:
            console.print("[red]Aborted — no content provided.[/red]")
            raise typer.Exit(1)
    else:
        content = f"---\ntitle: {title}\ncategory: {category}\ntags: [{tag_list}]\ncreated: {today}\n---\n\n# {title}\n\n{content}\n"

    target.write_text(content)
    console.print(f"[green]Created:[/green] {target.relative_to(Path.cwd())}")


@app.command("list")
def list_entries(
    category: str = typer.Option(None, "--category", "-c", help="Filter by category"),
    tag: str = typer.Option(None, "--tag", help="Filter by tag"),
):
    """List all knowledge entries."""
    entries = _all_entries()
    table = Table(title="Knowledge Base", show_lines=False)
    table.add_column("Category", style="cyan", no_wrap=True)
    table.add_column("Title", style="bold")
    table.add_column("Tags", style="dim")
    table.add_column("File", style="dim")

    count = 0
    for path in entries:
        meta = _parse_frontmatter(path)
        if category and meta["category"] != category:
            continue
        if tag and tag not in meta["tags"]:
            continue
        table.add_row(
            meta["category"],
            meta["title"],
            ", ".join(meta["tags"]),
            path.relative_to(KNOWLEDGE_DIR).as_posix(),
        )
        count += 1

    console.print(table)
    console.print(f"[dim]{count} entries[/dim]")


@app.command()
def search(query: str = typer.Argument(..., help="Search term")):
    """Search entry titles, tags, and content."""
    query_lower = query.lower()
    results = []
    for path in _all_entries():
        meta = _parse_frontmatter(path)
        body = path.read_text().lower()
        if (
            query_lower in meta["title"].lower()
            or any(query_lower in t for t in meta["tags"])
            or query_lower in body
        ):
            results.append((path, meta))

    if not results:
        console.print(f"[yellow]No entries matching '{query}'[/yellow]")
        raise typer.Exit(0)

    table = Table(title=f"Search: '{query}'", show_lines=False)
    table.add_column("Category", style="cyan", no_wrap=True)
    table.add_column("Title", style="bold")
    table.add_column("File", style="dim")
    for path, meta in results:
        table.add_row(meta["category"], meta["title"], path.relative_to(KNOWLEDGE_DIR).as_posix())
    console.print(table)


@app.command()
def show(file: str = typer.Argument(..., help="Relative path under knowledge/ or keyword")):
    """Show the contents of a knowledge entry."""
    target = KNOWLEDGE_DIR / file
    if not target.exists():
        # fuzzy: find first match by name
        matches = [p for p in _all_entries() if file.lower() in p.stem.lower()]
        if not matches:
            console.print(f"[red]Not found: {file}[/red]")
            raise typer.Exit(1)
        target = matches[0]

    console.print(Markdown(target.read_text()))


@app.command("rebuild-index")
def rebuild_index():
    """Print a knowledge index suitable for pasting into CLAUDE.md."""
    lines = ["\n## Knowledge base index\n"]
    for cat in CATEGORIES:
        entries = sorted((KNOWLEDGE_DIR / cat).glob("*.md"))
        if not entries:
            continue
        lines.append(f"\n### {cat.capitalize()}\n")
        for path in entries:
            meta = _parse_frontmatter(path)
            tags = ", ".join(meta["tags"])
            lines.append(f"- **{meta['title']}** — `knowledge/{cat}/{path.name}`  tags: {tags}")
    console.print("\n".join(lines))


if __name__ == "__main__":
    app()
