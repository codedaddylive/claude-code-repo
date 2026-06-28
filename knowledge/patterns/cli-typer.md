---
title: Typer CLI patterns
category: patterns
tags: [typer, cli, python]
created: 2026-06-28
---

# Typer CLI patterns

## App setup with sub-commands
```python
import typer
app = typer.Typer()

@app.command()
def analyze(
    source: str = typer.Argument(..., help="Path or URL to video"),
    max_frames: int = typer.Option(5, "--max-frames", help="Max frames to extract"),
    output: str = typer.Option(None, "--output", help="Output JSON path"),
):
    ...

if __name__ == "__main__":
    app()
```

## Rich progress + error display
```python
import typer
from rich.console import Console

console = Console()

def some_command():
    with typer.progressbar(items, label="Processing") as progress:
        for item in progress:
            ...
    typer.echo(typer.style("Done", fg=typer.colors.GREEN))
    console.print_exception()  # pretty tracebacks
```

## Notes
- `typer.Argument` = positional, `typer.Option` = flag
- Use `typer.Exit(code=1)` for error exits instead of `sys.exit`
- Rich console integrates cleanly with Typer for pretty output
