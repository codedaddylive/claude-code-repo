#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from video_tool.analyzer import assess_viability, generate_visual_summary, get_client, run_analysis
from video_tool.analyzer import encode_frame
from video_tool.downloader import download_github_release_asset, download_video, resolve_source
from video_tool.extractor import extract_audio, extract_frames, get_video_duration
from video_tool.models import AnalysisType, AnalyzeRequest, FrameSamplingStrategy
from video_tool.transcriber import transcribe

app = typer.Typer(
    name="video-tool",
    help="Analyze videos using Claude AI vision.",
    add_completion=False,
)
console = Console()


@app.command("analyze")
def cmd_analyze(
    source: str = typer.Argument(..., help="YouTube URL, video URL, or local file path"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Save JSON result to file"),
    analysis: list[AnalysisType] = typer.Option(
        [AnalysisType.FULL],
        "--analysis",
        "-a",
        help="Analysis types: keyframes, transcribe, objects, summary, full",
    ),
    interval: float = typer.Option(5.0, "--interval", "-i", help="Frame interval in seconds"),
    strategy: FrameSamplingStrategy = typer.Option(
        FrameSamplingStrategy.INTERVAL, "--strategy", "-s", help="Frame sampling strategy"
    ),
    max_frames: int = typer.Option(20, "--max-frames", "-m", help="Maximum frames to extract"),
    whisper_model: str = typer.Option("base", "--whisper-model", "-w", help="Whisper model size"),
):
    """Download and fully analyze a video using Claude AI."""
    with tempfile.TemporaryDirectory(prefix="video_tool_") as tmpdir:
        tmp = Path(tmpdir)
        try:
            with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
                task = progress.add_task("Resolving source...", total=None)

                src = resolve_source(source)

                progress.update(task, description="Downloading video...")
                video_path = download_video(src, tmp / "download")

                progress.update(task, description="Getting video info...")
                try:
                    duration = get_video_duration(video_path)
                except Exception:
                    duration = None

                progress.update(task, description="Extracting frames...")
                frames = extract_frames(
                    video_path, tmp / "frames",
                    strategy=strategy,
                    interval_sec=interval,
                    max_frames=max_frames,
                )

                transcription = None
                needs_transcription = AnalysisType.TRANSCRIBE in analysis or AnalysisType.FULL in analysis
                if needs_transcription:
                    progress.update(task, description="Extracting audio...")
                    audio_path = extract_audio(video_path, tmp / "audio.wav")
                    if audio_path:
                        progress.update(task, description="Transcribing audio (this may take a moment)...")
                        transcription = transcribe(audio_path, model_name=whisper_model)

                progress.update(task, description="Analyzing with Claude AI...")
                result = run_analysis(
                    frames=frames,
                    analysis_types=list(analysis),
                    source_str=source,
                    duration_sec=duration,
                    transcription=transcription,
                )

            result_json = result.model_dump_json(indent=2)
            if output:
                output.write_text(result_json)
                console.print(f"[green]Result saved to {output}[/green]")
            else:
                console.print_json(result_json)

        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(code=1)


@app.command("extract-frames")
def cmd_extract_frames(
    source: str = typer.Argument(..., help="YouTube URL, video URL, or local file path"),
    output_dir: Path = typer.Option(Path("./frames"), "--output-dir", "-o", help="Output directory for frames"),
    interval: float = typer.Option(5.0, "--interval", "-i", help="Frame interval in seconds"),
    max_frames: int = typer.Option(20, "--max-frames", "-m", help="Maximum frames to extract"),
    strategy: FrameSamplingStrategy = typer.Option(
        FrameSamplingStrategy.INTERVAL, "--strategy", "-s"
    ),
):
    """Extract frames from a video without AI analysis."""
    with tempfile.TemporaryDirectory(prefix="video_tool_") as tmpdir:
        tmp = Path(tmpdir)
        try:
            with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
                task = progress.add_task("Downloading video...", total=None)
                src = resolve_source(source)
                video_path = download_video(src, tmp / "download")

                progress.update(task, description="Extracting frames...")
                output_dir.mkdir(parents=True, exist_ok=True)
                frames = extract_frames(
                    video_path, output_dir,
                    strategy=strategy,
                    interval_sec=interval,
                    max_frames=max_frames,
                )

            console.print(f"[green]Extracted {len(frames)} frames to {output_dir}[/green]")
            for f in frames:
                console.print(f"  {f.file_path} (t={f.timestamp_sec:.1f}s)")

        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(code=1)


@app.command("transcribe")
def cmd_transcribe(
    source: str = typer.Argument(..., help="YouTube URL, video URL, or local file path"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Save transcript JSON to file"),
    model: str = typer.Option("base", "--model", "-m", help="Whisper model size (tiny/base/small/medium/large)"),
    language: Optional[str] = typer.Option(None, "--language", "-l", help="Language code (e.g. 'en'). Auto-detects if omitted."),
):
    """Transcribe audio from a video using Whisper."""
    with tempfile.TemporaryDirectory(prefix="video_tool_") as tmpdir:
        tmp = Path(tmpdir)
        try:
            with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
                task = progress.add_task("Downloading video...", total=None)
                src = resolve_source(source)
                video_path = download_video(src, tmp / "download")

                progress.update(task, description="Extracting audio...")
                audio_path = extract_audio(video_path, tmp / "audio.wav")
                if not audio_path:
                    console.print("[yellow]No audio track found in this video.[/yellow]")
                    raise typer.Exit(code=1)

                progress.update(task, description="Transcribing (this may take a moment)...")
                result = transcribe(audio_path, model_name=model, language=language)

            if not result:
                console.print("[yellow]Transcription produced no output.[/yellow]")
                raise typer.Exit(code=1)

            result_json = result.model_dump_json(indent=2)
            if output:
                output.write_text(result_json)
                console.print(f"[green]Transcript saved to {output}[/green]")
            else:
                console.print_json(result_json)

        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(code=1)


@app.command("viability")
def cmd_viability(
    source: str = typer.Argument(..., help="Video link (YouTube, Twitter/X, direct URL) or local file"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Save verdict JSON to file"),
    whisper_model: str = typer.Option("base", "--whisper-model", "-w", help="Whisper model size"),
    cookies: Optional[Path] = typer.Option(None, "--cookies", help="Cookies file for auth-walled links (Twitter/X)"),
    max_frames: int = typer.Option(8, "--max-frames", "-m", help="Frames for visual fallback if no audio"),
):
    """Ingest a link and judge whether it's a viable development improvement."""
    with tempfile.TemporaryDirectory(prefix="video_tool_") as tmpdir:
        tmp = Path(tmpdir)
        try:
            with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
                task = progress.add_task("Resolving source...", total=None)
                src = resolve_source(source)
                progress.update(task, description="Downloading...")
                video_path = download_video(src, tmp / "download", cookies_file=cookies)
                assessment = _assess_video(video_path, source, tmp, whisper_model, max_frames, progress, task)

            _finish_verdict(assessment, output)

        except Exception as e:
            msg = str(e)
            console.print(f"[red]Error:[/red] {msg}")
            if _looks_like_youtube(source) and ("403" in msg or "Forbidden" in msg or "Sign in" in msg):
                console.print(
                    "[yellow]YouTube blocks datacenter IPs. Run on an open network, pass --cookies, "
                    "or use 'viability-release' to analyze a file staged on GitHub.[/yellow]"
                )
            raise typer.Exit(code=1)


@app.command("viability-release")
def cmd_viability_release(
    repo: str = typer.Argument(..., help="owner/repo hosting the release (e.g. codedaddylive/claude-code-repo)"),
    tag: str = typer.Argument(..., help="Release tag holding the video asset"),
    pattern: str = typer.Option("*.mp4", "--pattern", "-p", help="Asset filename glob to match"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Save verdict JSON to file"),
    whisper_model: str = typer.Option("base", "--whisper-model", "-w", help="Whisper model size"),
    max_frames: int = typer.Option(8, "--max-frames", "-m", help="Frames for visual fallback if no audio"),
):
    """Judge viability of a video staged as a GitHub release asset (bypasses blocked video hosts)."""
    with tempfile.TemporaryDirectory(prefix="video_tool_") as tmpdir:
        tmp = Path(tmpdir)
        try:
            with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
                task = progress.add_task(f"Fetching {pattern} from {repo}@{tag}...", total=None)
                video_path = download_github_release_asset(repo, tag, tmp / "download", pattern=pattern)
                label = f"{repo}@{tag}:{video_path.name}"
                assessment = _assess_video(video_path, label, tmp, whisper_model, max_frames, progress, task)

            _finish_verdict(assessment, output)

        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(code=1)


def _assess_video(video_path, source_label, tmp, whisper_model, max_frames, progress, task):
    progress.update(task, description="Extracting audio...")
    audio_path = extract_audio(video_path, tmp / "audio.wav")

    content = ""
    if audio_path:
        progress.update(task, description="Transcribing (this may take a moment)...")
        transcription = transcribe(audio_path, model_name=whisper_model)
        if transcription and transcription.full_text.strip():
            content = transcription.full_text

    if not content:
        progress.update(task, description="No usable audio — summarizing visually...")
        frames = extract_frames(video_path, tmp / "frames", max_frames=max_frames)
        encoded = [encode_frame(f) for f in frames]
        content = generate_visual_summary(get_client(), encoded)

    progress.update(task, description="Assessing viability...")
    return assess_viability(source_label, content)


def _finish_verdict(assessment, output: Optional[Path]) -> None:
    _print_verdict(assessment)
    if output:
        output.write_text(assessment.model_dump_json(indent=2))
        console.print(f"[green]Verdict saved to {output}[/green]")


def _looks_like_youtube(source: str) -> bool:
    return "youtube.com" in source or "youtu.be" in source


def _print_verdict(a) -> None:
    colors = {"adopt": "green", "investigate": "yellow", "skip": "red"}
    color = colors.get(a.verdict.value, "white")
    console.print(f"\n[bold {color}]VERDICT: {a.verdict.value.upper()}[/bold {color}]  (confidence {a.confidence:.0%})")
    console.print(f"[bold]Source:[/bold] {a.source}")
    console.print(f"[bold]Reasoning:[/bold] {a.reasoning}")
    if a.relevant_to_stack:
        console.print(f"[bold]Touches:[/bold] {', '.join(a.relevant_to_stack)}")
    if a.verdict.value == "adopt" and a.suggested_title:
        console.print(
            f"[bold]Encode it:[/bold] python brain.py add "
            f"--title \"{a.suggested_title}\" --category {a.suggested_category or 'architecture'}"
        )


if __name__ == "__main__":
    app()
