#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.markup import escape
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .agent import AriaAgent
from .config import load_settings
from .ingest import ingest_repo
from .llm import make_llm_backend
from .models import AriaError
from .team import TeamJudge, load_catalog

app = typer.Typer(
    name="aria",
    help="Aria — an open-source AI assistant over GitHub repositories.",
    add_completion=False,
)
console = Console()


def _agent() -> AriaAgent:
    return AriaAgent.load(load_settings())


@app.command("ingest")
def cmd_ingest(
    sources: list[str] = typer.Argument(
        ..., help="Repos to index: GitHub URL, owner/repo, or local path."
    ),
):
    """Clone and index one or more repositories into Aria's knowledge base."""
    agent = _agent()
    try:
        for source in sources:
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}"),
                BarColumn(),
                TextColumn("{task.completed}/{task.total}"),
                console=console,
            ) as progress:
                task = progress.add_task(f"Ingesting {source}", total=None)

                def on_progress(done: int, total: int, rel: str) -> None:
                    progress.update(task, total=total, completed=done,
                                    description=f"Indexing {rel[:48]}")

                stats = ingest_repo(source, agent.settings, agent.store,
                                    agent.embedder, on_progress=on_progress)
            console.print(
                f"[green]✓[/green] Indexed [bold]{stats.repo}[/bold]: "
                f"{stats.files} files, {stats.chunks} chunks"
            )
        agent.save()
        console.print(f"[dim]Index saved to {agent.settings.index_dir}[/dim]")
    except AriaError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command("ask")
def cmd_ask(
    question: str = typer.Argument(..., help="Your question about the indexed repos."),
    no_sources: bool = typer.Option(False, "--no-sources", help="Hide the source list."),
):
    """Ask Aria a one-off question and stream the answer."""
    agent = _agent()
    if len(agent.store) == 0:
        console.print("[yellow]No repositories indexed yet. Run 'aria ingest <repo>' first.[/yellow]")
        raise typer.Exit(code=1)
    try:
        stream, sources = agent.ask_stream(question)
        console.print("[bold cyan]Aria:[/bold cyan]")
        for piece in stream:
            console.print(piece, end="")
        console.print()
        if sources and not no_sources:
            _print_sources(sources)
    except AriaError as e:
        console.print(f"\n[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command("chat")
def cmd_chat():
    """Start an interactive chat session over the indexed repositories."""
    agent = _agent()
    if len(agent.store) == 0:
        console.print("[yellow]No repositories indexed yet. Run 'aria ingest <repo>' first.[/yellow]")
        raise typer.Exit(code=1)
    console.print("[bold cyan]Aria[/bold cyan] — ask about your repos. Type 'exit' to quit.\n")
    while True:
        try:
            question = console.input("[bold green]you >[/bold green] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]bye[/dim]")
            break
        if question.lower() in {"exit", "quit", ":q"}:
            break
        if not question:
            continue
        try:
            stream, sources = agent.ask_stream(question)
            console.print("[bold cyan]aria >[/bold cyan] ", end="")
            for piece in stream:
                console.print(piece, end="")
            console.print()
            if sources:
                _print_sources(sources)
        except AriaError as e:
            console.print(f"[red]Error:[/red] {e}")
        console.print()


@app.command("status")
def cmd_status():
    """Show what has been indexed and the active configuration."""
    settings = load_settings()
    agent = AriaAgent.load(settings)

    cfg = Table(title="Aria configuration", show_header=False)
    cfg.add_row("LLM backend", f"{settings.llm_backend} ({settings.model})")
    cfg.add_row("Embeddings", f"{settings.embed_backend} ({settings.embed_model})")
    cfg.add_row("Data dir", str(settings.data_dir))
    console.print(cfg)

    repos = agent.stats()
    if not repos:
        console.print("[yellow]No repositories indexed.[/yellow]")
        return
    table = Table(title="Indexed repositories")
    table.add_column("Repository", style="bold")
    table.add_column("Files", justify="right")
    table.add_column("Chunks", justify="right")
    for r in repos:
        table.add_row(r.repo, str(r.files), str(r.chunks))
    console.print(table)


@app.command("remove")
def cmd_remove(repo: str = typer.Argument(..., help="Repository name to remove (owner/repo).")):
    """Remove an indexed repository from the knowledge base."""
    agent = _agent()
    removed = agent.store.delete_repo(repo)
    if removed:
        agent.save()
        console.print(f"[green]Removed {removed} chunks for {repo}.[/green]")
    else:
        console.print(f"[yellow]No indexed content found for '{repo}'.[/yellow]")


team_app = typer.Typer(
    name="team",
    help="Assemble an AI team of free, open-source models (LLM-as-a-judge).",
    add_completion=False,
)
app.add_typer(team_app)


@team_app.command("recommend")
def cmd_team_recommend(
    method: str = typer.Option(
        "auto", "--judge", "-j",
        help="Scoring mode: auto (LLM, heuristic fallback) | llm | heuristic.",
    ),
    include_noncommercial: bool = typer.Option(
        False, "--include-noncommercial",
        help="Also consider open-weight models whose license forbids commercial use.",
    ),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Save roster as JSON."),
):
    """Pick the best free/open-source model for each role and print the team."""
    if method not in ("auto", "llm", "heuristic"):
        console.print("[red]--judge must be one of: auto, llm, heuristic[/red]")
        raise typer.Exit(code=1)
    settings = load_settings()
    judge = TeamJudge(make_llm_backend(settings))
    try:
        with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as p:
            p.add_task(f"Judging candidates ({method})...", total=None)
            roster = judge.recommend(method=method, include_noncommercial=include_noncommercial)
    except AriaError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)

    table = Table(title=f"Aria AI team — free & open-source (judge: {roster.method})")
    table.add_column("Role", style="bold")
    table.add_column("Pick", style="cyan")
    table.add_column("Score", justify="right")
    table.add_column("Runners-up", style="dim")
    for pick in roster.picks:
        runners = ", ".join(f"{escape(c.name)} ({c.score:g})" for c in pick.runners_up)
        table.add_row(pick.role_name, escape(pick.winner_name), f"{pick.score:g}", runners or "—")
    console.print(table)
    console.print("\n[dim]Why each pick:[/dim]")
    for pick in roster.picks:
        console.print(
            f"  [bold]{pick.role_name}[/bold] → [cyan]{escape(pick.winner_name)}[/cyan]: "
            f"{escape(pick.reason)}"
        )

    if output:
        output.write_text(roster.model_dump_json(indent=2))
        console.print(f"\n[green]Roster saved to {output}[/green]")
    console.print(
        "\n[dim]Ratings are qualitative; verify on live leaderboards (LMArena, "
        "OpenLLM Leaderboard, Aider/SWE-bench). Edit aria/data/models.json to add "
        "or re-rank models.[/dim]"
    )


@team_app.command("models")
def cmd_team_models(
    role: Optional[str] = typer.Option(None, "--role", "-r", help="Filter to one role id."),
):
    """List the open-source model catalog the judge chooses from."""
    catalog = load_catalog()
    if role:
        try:
            r = catalog.role(role)
        except AriaError as e:
            console.print(f"[red]{e}[/red] Roles: {', '.join(x.id for x in catalog.roles)}")
            raise typer.Exit(code=1)
        cards = [m for m in catalog.models if m.modality == r.modality]
        title = f"Models for role '{r.name}'"
    else:
        cards = catalog.models
        title = "Open-source model catalog"

    table = Table(title=title)
    table.add_column("Model", style="bold cyan")
    table.add_column("Provider")
    table.add_column("License")
    table.add_column("Free comm.", justify="center")
    table.add_column("Modality")
    for m in cards:
        table.add_row(escape(m.name), m.provider, escape(m.license),
                      m.free_commercial_use, m.modality)
    console.print(table)


def _print_sources(sources) -> None:
    table = Table(title="Sources", show_edge=False, pad_edge=False)
    table.add_column("score", justify="right", style="dim")
    table.add_column("location", style="cyan")
    for r in sources:
        table.add_row(f"{r.score:.3f}", r.chunk.citation)
    console.print(table)


if __name__ == "__main__":
    app()
