#!/usr/bin/env python3
"""
Brain CLI — 5-step knowledge system.

  BASE    knowledge/ (Wiki) + raw/ (Raw data lake)
  UPLOAD  brain.py upload / ingest — bulk-ingest files into the queue
  INFLOW  brain.py inflow — manage automated data pipelines
  LOOP    brain.py queue / approve / reject — 3-bucket review loop
  DRIVE   brain.py list / search / show / add — consume the knowledge
"""

import json
import re
import uuid
from datetime import date, datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(help="Brain — knowledge base + ingestion pipeline.", add_completion=False)
console = Console()

ROOT          = Path(__file__).parent
KNOWLEDGE_DIR = ROOT / "knowledge"
RAW_DIR       = ROOT / "raw"
INBOX_DIR     = RAW_DIR / "_inbox"
QUEUE_FILE    = RAW_DIR / "_queue.json"
INFLOW_FILE   = RAW_DIR / "_inflow.json"
CATEGORIES    = ["patterns", "apis", "architecture", "domain"]

# ── Helpers ──────────────────────────────────────────────────────────────────

def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _today() -> str:
    return date.today().isoformat()


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
            key, val = key.strip(), val.strip()
            if key == "tags":
                meta["tags"] = [t.strip(" []") for t in val.split(",") if t.strip(" []")]
            else:
                meta[key] = val
    return meta


def _load_queue() -> dict:
    if QUEUE_FILE.exists():
        return json.loads(QUEUE_FILE.read_text())
    return {"items": []}


def _save_queue(q: dict) -> None:
    QUEUE_FILE.write_text(json.dumps(q, indent=2))


def _load_inflow() -> dict:
    if INFLOW_FILE.exists():
        return json.loads(INFLOW_FILE.read_text())
    return {"sources": [], "last_run": None}


def _save_inflow(cfg: dict) -> None:
    INFLOW_FILE.write_text(json.dumps(cfg, indent=2))


def _classify(title: str, body: str) -> tuple[str, str]:
    """
    Simple heuristic 3-bucket classifier.
    Returns (status, reason).
    Bucket meanings:
      auto_approve  — low-stakes, clear pattern; promote immediately
      need_signoff  — higher-stakes edit; human must approve
      need_context  — too sparse; human must supply more info
    """
    word_count = len(body.split())
    has_code   = "```" in body
    has_header = "##" in body

    if word_count < 40:
        return "need_context", f"Only {word_count} words — too sparse to be useful"
    if word_count >= 150 and (has_code or has_header):
        return "auto_approve", "Rich content with code/structure — low risk to promote"
    return "need_signoff", "Moderate content — review before promoting to Wiki"


def _promote(item: dict) -> Path:
    """Write a queued draft to knowledge/ and return the path."""
    d      = item["draft"]
    cat    = d.get("category", "domain")
    slug   = _slug(d["title"])
    target = KNOWLEDGE_DIR / cat / f"{slug}.md"
    tags   = ", ".join(d.get("tags", []))
    source = item.get("source", "")
    today  = _today()
    content = (
        f"---\ntitle: {d['title']}\ncategory: {cat}\n"
        f"tags: [{tags}]\ncreated: {today}"
        + (f"\nsource: {source}" if source else "")
        + f"\n---\n\n{d['body'].strip()}\n"
    )
    target.write_text(content)
    return target


# ── UPLOAD ───────────────────────────────────────────────────────────────────

@app.command()
def upload(
    source: str = typer.Argument(..., help="File path to ingest"),
    title:    str = typer.Option(None,  "--title",    "-t", help="Override title"),
    category: str = typer.Option(None,  "--category", "-c", help="patterns|apis|architecture|domain"),
    tags:     str = typer.Option("",    "--tags",          help="Comma-separated tags"),
    bucket:   str = typer.Option(None,  "--bucket",        help="Force bucket: auto_approve|need_signoff|need_context"),
):
    """Ingest a single file into the review queue (UPLOAD step)."""
    path = Path(source)
    if not path.exists():
        console.print(f"[red]File not found: {source}[/red]")
        raise typer.Exit(1)

    body  = path.read_text(errors="replace")
    title = title or path.stem.replace("-", " ").replace("_", " ").title()
    cat   = category or "domain"

    if cat not in CATEGORIES:
        console.print(f"[red]Unknown category '{cat}'. Choose: {', '.join(CATEGORIES)}[/red]")
        raise typer.Exit(1)

    status, reason = _classify(title, body)
    if bucket:
        status, reason = bucket, "manually forced"

    tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    item = {
        "id":      str(uuid.uuid4())[:8],
        "source":  str(path),
        "created": _today(),
        "status":  status,
        "reason":  reason,
        "draft": {
            "title":    title,
            "category": cat,
            "tags":     tag_list,
            "body":     body,
        },
    }

    q = _load_queue()
    q["items"].append(item)
    _save_queue(q)

    color = {"auto_approve": "green", "need_signoff": "yellow", "need_context": "red"}.get(status, "white")
    console.print(f"[{color}][{status.upper()}][/{color}] id={item['id']}  {title}")
    console.print(f"  [dim]{reason}[/dim]")

    if status == "auto_approve":
        promoted = _promote(item)
        q["items"][-1]["status"] = "approved"
        _save_queue(q)
        console.print(f"  [green]Auto-promoted →[/green] {promoted.relative_to(ROOT)}")


@app.command()
def ingest(
    move: bool = typer.Option(False, "--move", help="Move files out of inbox after ingestion"),
):
    """Process all files in raw/_inbox/ into the review queue (UPLOAD step)."""
    files = [f for f in INBOX_DIR.iterdir() if f.is_file() and not f.name.startswith(".")]
    if not files:
        console.print("[dim]Inbox is empty. Drop files into raw/_inbox/ to begin.[/dim]")
        return

    console.print(f"[bold]Ingesting {len(files)} file(s) from inbox…[/bold]")
    q = _load_queue()

    for path in sorted(files):
        body   = path.read_text(errors="replace")
        title  = path.stem.replace("-", " ").replace("_", " ").title()
        status, reason = _classify(title, body)

        item = {
            "id":      str(uuid.uuid4())[:8],
            "source":  path.name,
            "created": _today(),
            "status":  status,
            "reason":  reason,
            "draft": {
                "title":    title,
                "category": "domain",
                "tags":     [],
                "body":     body,
            },
        }
        q["items"].append(item)

        color = {"auto_approve": "green", "need_signoff": "yellow", "need_context": "red"}.get(status, "white")
        console.print(f"  [{color}]{status.upper():14}[/{color}] {path.name}")

        if status == "auto_approve":
            promoted = _promote(item)
            item["status"] = "approved"
            console.print(f"               [green]→ {promoted.relative_to(ROOT)}[/green]")

        if move:
            path.rename(RAW_DIR / path.parent.name.lstrip("_") or RAW_DIR / "ecosystem" / path.name)

    _save_queue(q)
    pending = [i for i in q["items"] if i["status"] in ("need_signoff", "need_context")]
    console.print(f"\n[bold]{len(pending)} item(s) pending review.[/bold] Run: [cyan]python brain.py queue[/cyan]")


# ── INFLOW ────────────────────────────────────────────────────────────────────

inflow_app = typer.Typer(help="Manage automated data pipelines (INFLOW step).")
app.add_typer(inflow_app, name="inflow")

SOURCE_TYPES = ["folder", "slack-export", "transcript", "feed", "email-export", "manual"]


@inflow_app.command("add")
def inflow_add(
    name:   str = typer.Option(..., "--name", "-n", prompt=True, help="Pipeline name"),
    source: str = typer.Option(..., "--source", "-s", prompt=True,
                               help=f"Source type: {', '.join(SOURCE_TYPES)}"),
    path:   str = typer.Option(..., "--path", "-p", prompt=True,
                               help="File path or folder to watch"),
    tags:   str = typer.Option("", "--tags", help="Auto-tags for ingested items"),
    category: str = typer.Option("domain", "--category", "-c"),
):
    """Register a new data source pipeline."""
    cfg = _load_inflow()
    cfg["sources"].append({
        "name":     name,
        "type":     source,
        "path":     path,
        "tags":     [t.strip() for t in tags.split(",") if t.strip()],
        "category": category,
        "added":    _today(),
        "active":   True,
    })
    _save_inflow(cfg)
    console.print(f"[green]Pipeline registered:[/green] {name} ({source}) → {path}")


@inflow_app.command("list")
def inflow_list():
    """List configured data pipelines."""
    cfg = _load_inflow()
    if not cfg["sources"]:
        console.print("[dim]No pipelines configured. Run: python brain.py inflow add[/dim]")
        return
    table = Table(title="Inflow Pipelines")
    table.add_column("Name", style="bold")
    table.add_column("Type", style="cyan")
    table.add_column("Path", style="dim")
    table.add_column("Category")
    table.add_column("Tags", style="dim")
    table.add_column("Active")
    for s in cfg["sources"]:
        table.add_row(
            s["name"], s["type"], s["path"], s["category"],
            ", ".join(s.get("tags", [])),
            "[green]yes[/green]" if s.get("active") else "[red]no[/red]",
        )
    console.print(table)
    if cfg["last_run"]:
        console.print(f"[dim]Last run: {cfg['last_run']}[/dim]")


@inflow_app.command("run")
def inflow_run(
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without ingesting"),
):
    """Pull from all active pipelines into the inbox."""
    cfg = _load_inflow()
    active = [s for s in cfg["sources"] if s.get("active")]
    if not active:
        console.print("[yellow]No active pipelines. Add one: python brain.py inflow add[/yellow]")
        return

    total = 0
    for source in active:
        src_path = Path(source["path"])
        if not src_path.exists():
            console.print(f"[yellow]Skipping {source['name']} — path not found: {src_path}[/yellow]")
            continue

        files = list(src_path.glob("*")) if src_path.is_dir() else [src_path]
        files = [f for f in files if f.is_file()]
        console.print(f"[cyan]{source['name']}[/cyan] ({source['type']}) — {len(files)} file(s)")

        for f in files:
            if not dry_run:
                dest = INBOX_DIR / f.name
                if not dest.exists():
                    dest.write_bytes(f.read_bytes())
                    console.print(f"  → inbox: {f.name}")
                    total += 1
            else:
                console.print(f"  [dim](dry-run) {f.name}[/dim]")
                total += 1

    cfg["last_run"] = datetime.now().isoformat(timespec="seconds")
    _save_inflow(cfg)

    if not dry_run and total:
        console.print(f"\n[bold]{total} file(s) copied to inbox.[/bold] Run: [cyan]python brain.py ingest[/cyan]")


# ── LOOP (review queue) ───────────────────────────────────────────────────────

@app.command()
def queue(
    status: str = typer.Option(None, "--status", "-s",
                               help="Filter: auto_approve|need_signoff|need_context|approved|rejected"),
):
    """Show the 3-bucket review queue (LOOP step)."""
    q = _load_queue()
    items = q["items"]

    buckets = {
        "auto_approve":  ("green",  "AUTO-APPROVE"),
        "need_signoff":  ("yellow", "NEED SIGNOFF"),
        "need_context":  ("red",    "MORE CONTEXT"),
        "approved":      ("dim",    "APPROVED"),
        "rejected":      ("dim",    "REJECTED"),
    }

    if status:
        items = [i for i in items if i["status"] == status]

    if not items:
        console.print("[dim]Queue is empty.[/dim]")
        return

    table = Table(title="Review Queue", show_lines=True)
    table.add_column("ID",       style="bold",  no_wrap=True)
    table.add_column("Bucket",   no_wrap=True)
    table.add_column("Title")
    table.add_column("Category", style="cyan",  no_wrap=True)
    table.add_column("Reason",   style="dim")
    table.add_column("Created",  style="dim",   no_wrap=True)

    for item in items:
        color, label = buckets.get(item["status"], ("white", item["status"].upper()))
        table.add_row(
            item["id"],
            f"[{color}]{label}[/{color}]",
            item["draft"]["title"],
            item["draft"].get("category", ""),
            item.get("reason", ""),
            item.get("created", ""),
        )
    console.print(table)

    pending   = [i for i in q["items"] if i["status"] == "need_signoff"]
    no_ctx    = [i for i in q["items"] if i["status"] == "need_context"]
    if pending:
        console.print(f"[yellow]{len(pending)} need signoff.[/yellow] Run: [cyan]python brain.py review[/cyan]")
    if no_ctx:
        console.print(f"[red]{len(no_ctx)} need more context.[/red] Edit in raw/_queue.json and re-classify.")


@app.command()
def review():
    """Interactively review need_signoff items (LOOP step)."""
    q       = _load_queue()
    pending = [i for i in q["items"] if i["status"] == "need_signoff"]

    if not pending:
        console.print("[green]Nothing pending review.[/green]")
        return

    console.print(f"[bold]{len(pending)} item(s) to review.[/bold]  a=approve  r=reject  s=skip  q=quit\n")

    for item in pending:
        console.print(Panel(
            f"[bold]{item['draft']['title']}[/bold]\n"
            f"[cyan]Category:[/cyan] {item['draft'].get('category', '—')}  "
            f"[cyan]Tags:[/cyan] {', '.join(item['draft'].get('tags', []))}\n"
            f"[dim]{item.get('reason', '')}[/dim]\n\n"
            + item["draft"]["body"][:600]
            + (" …" if len(item["draft"]["body"]) > 600 else ""),
            title=f"[bold]ID: {item['id']}[/bold]",
            border_style="yellow",
        ))

        action = typer.prompt("Action", default="s").strip().lower()

        if action == "a":
            promoted = _promote(item)
            item["status"] = "approved"
            console.print(f"[green]Approved →[/green] {promoted.relative_to(ROOT)}")
        elif action == "r":
            item["status"] = "rejected"
            console.print("[red]Rejected.[/red]")
        elif action == "q":
            break
        else:
            console.print("[dim]Skipped.[/dim]")

    _save_queue(q)


@app.command()
def approve(
    item_id: str = typer.Argument(..., help="Queue item ID"),
    category: str = typer.Option(None, "--category", "-c"),
    tags:     str = typer.Option(None, "--tags"),
):
    """Approve a specific queued item and promote it to knowledge/ (LOOP step)."""
    q = _load_queue()
    for item in q["items"]:
        if item["id"] == item_id:
            if item["status"] == "approved":
                console.print(f"[yellow]Already approved.[/yellow]")
                raise typer.Exit(0)
            if category:
                item["draft"]["category"] = category
            if tags:
                item["draft"]["tags"] = [t.strip() for t in tags.split(",") if t.strip()]
            promoted = _promote(item)
            item["status"] = "approved"
            _save_queue(q)
            console.print(f"[green]Approved →[/green] {promoted.relative_to(ROOT)}")
            return
    console.print(f"[red]ID not found: {item_id}[/red]")
    raise typer.Exit(1)


@app.command()
def reject(item_id: str = typer.Argument(..., help="Queue item ID")):
    """Reject a queued item."""
    q = _load_queue()
    for item in q["items"]:
        if item["id"] == item_id:
            item["status"] = "rejected"
            _save_queue(q)
            console.print(f"[red]Rejected:[/red] {item['draft']['title']}")
            return
    console.print(f"[red]ID not found: {item_id}[/red]")
    raise typer.Exit(1)


# ── DRIVE (read + manage the Wiki) ───────────────────────────────────────────

@app.command()
def add(
    title:    str = typer.Option(..., "--title",    "-t", prompt=True),
    category: str = typer.Option(..., "--category", "-c", prompt=True,
                                  help=f"Category: {', '.join(CATEGORIES)}"),
    tags:     str = typer.Option("", "--tags"),
    content:  str = typer.Option(None, "--content", help="Body text (omit to open $EDITOR)"),
):
    """Add a knowledge entry directly (bypasses the queue)."""
    if category not in CATEGORIES:
        console.print(f"[red]Unknown category. Choose: {', '.join(CATEGORIES)}[/red]")
        raise typer.Exit(1)

    target = KNOWLEDGE_DIR / category / f"{_slug(title)}.md"
    if target.exists():
        console.print(f"[yellow]Entry already exists: {target.relative_to(ROOT)}[/yellow]")
        raise typer.Exit(1)

    tag_list = ", ".join(t.strip() for t in tags.split(",") if t.strip())
    today    = _today()
    template = f"---\ntitle: {title}\ncategory: {category}\ntags: [{tag_list}]\ncreated: {today}\n---\n\n# {title}\n\n"

    if content is None:
        content = typer.edit(template)
        if not content:
            console.print("[red]Aborted — no content provided.[/red]")
            raise typer.Exit(1)
    else:
        content = template + content + "\n"

    target.write_text(content)
    console.print(f"[green]Created:[/green] {target.relative_to(ROOT)}")


@app.command("list")
def list_entries(
    category: str = typer.Option(None, "--category", "-c"),
    tag:      str = typer.Option(None, "--tag"),
):
    """List all knowledge entries."""
    table = Table(title="Knowledge Base (Wiki)", show_lines=False)
    table.add_column("Category", style="cyan", no_wrap=True)
    table.add_column("Title",    style="bold")
    table.add_column("Tags",     style="dim")
    table.add_column("File",     style="dim")

    count = 0
    for path in _all_entries():
        meta = _parse_frontmatter(path)
        if category and meta["category"] != category:
            continue
        if tag and tag not in meta["tags"]:
            continue
        table.add_row(meta["category"], meta["title"], ", ".join(meta["tags"]),
                      path.relative_to(KNOWLEDGE_DIR).as_posix())
        count += 1

    console.print(table)
    console.print(f"[dim]{count} entries[/dim]")


@app.command()
def search(query: str = typer.Argument(..., help="Search term")):
    """Search entry titles, tags, and content."""
    query_lower = query.lower()
    results = [
        (p, _parse_frontmatter(p))
        for p in _all_entries()
        if query_lower in p.read_text().lower()
        or query_lower in _parse_frontmatter(p)["title"].lower()
    ]
    if not results:
        console.print(f"[yellow]No entries matching '{query}'[/yellow]")
        raise typer.Exit(0)

    table = Table(title=f"Search: '{query}'")
    table.add_column("Category", style="cyan", no_wrap=True)
    table.add_column("Title",    style="bold")
    table.add_column("File",     style="dim")
    for path, meta in results:
        table.add_row(meta["category"], meta["title"], path.relative_to(KNOWLEDGE_DIR).as_posix())
    console.print(table)


@app.command()
def show(file: str = typer.Argument(..., help="knowledge/ relative path or keyword")):
    """Show a knowledge entry."""
    target = KNOWLEDGE_DIR / file
    if not target.exists():
        matches = [p for p in _all_entries() if file.lower() in p.stem.lower()]
        if not matches:
            console.print(f"[red]Not found: {file}[/red]")
            raise typer.Exit(1)
        target = matches[0]
    console.print(Markdown(target.read_text()))


@app.command("rebuild-index")
def rebuild_index():
    """Print knowledge index for CLAUDE.md."""
    lines = ["\n### Knowledge base index\n"]
    for cat in CATEGORIES:
        entries = sorted((KNOWLEDGE_DIR / cat).glob("*.md"))
        if not entries:
            continue
        lines.append(f"\n#### {cat.capitalize()}\n")
        for path in entries:
            meta = _parse_frontmatter(path)
            tags = ", ".join(meta["tags"])
            lines.append(f"- **{meta['title']}** — `knowledge/{cat}/{path.name}`  tags: {tags}")
    console.print("\n".join(lines))


@app.command()
def status():
    """Show a summary of the brain system state."""
    wiki_count  = len(_all_entries())
    inbox_count = len([f for f in INBOX_DIR.iterdir() if f.is_file()]) if INBOX_DIR.exists() else 0
    q           = _load_queue()
    cfg         = _load_inflow()

    buckets = {"need_signoff": 0, "need_context": 0, "auto_approve": 0, "approved": 0, "rejected": 0}
    for item in q["items"]:
        buckets[item.get("status", "need_signoff")] = buckets.get(item.get("status"), 0) + 1

    console.print(Panel(
        f"[bold cyan]Wiki[/bold cyan]       {wiki_count} entries in knowledge/\n"
        f"[bold cyan]Inbox[/bold cyan]      {inbox_count} file(s) in raw/_inbox/\n"
        f"[bold cyan]Pipelines[/bold cyan]  {len(cfg['sources'])} configured "
        f"({sum(1 for s in cfg['sources'] if s.get('active'))} active)\n"
        f"\n[bold]Queue[/bold]\n"
        f"  [green]Auto-approved:[/green]  {buckets['auto_approve']}\n"
        f"  [yellow]Need signoff:[/yellow]   {buckets['need_signoff']}\n"
        f"  [red]Need context:[/red]   {buckets['need_context']}\n"
        f"  [dim]Approved:  {buckets['approved']}   Rejected: {buckets['rejected']}[/dim]",
        title="[bold]Brain Status[/bold]",
        border_style="cyan",
    ))


if __name__ == "__main__":
    app()
