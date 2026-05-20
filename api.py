from __future__ import annotations

import asyncio
import tempfile
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import aiofiles
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from video_tool.analyzer import run_analysis
from video_tool.downloader import download_video, resolve_source
from video_tool.extractor import extract_audio, extract_frames, get_video_duration
from video_tool.models import (
    AnalysisResult,
    AnalysisType,
    AnalyzeRequest,
    AnalyzeResponse,
    FrameSamplingStrategy,
)
from video_tool.transcriber import load_model, transcribe

_jobs: dict[str, AnalyzeResponse] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-warm Whisper base model so first request isn't slow
    await asyncio.get_event_loop().run_in_executor(None, load_model, "base")
    yield


app = FastAPI(
    title="Video Analysis API",
    description="Extract and analyze videos using Claude AI vision and Whisper transcription.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    return {"status": "ok", "model": "claude-sonnet-4-6"}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_video(request: AnalyzeRequest):
    """
    Analyze a video from a URL. Accepts YouTube, yt-dlp-supported platforms,
    and direct video file URLs.

    Set a high HTTP timeout (~300s) for long videos.
    """
    job_id = str(uuid.uuid4())
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _sync_pipeline, request)
        response = AnalyzeResponse(job_id=job_id, status="completed", result=result)
    except Exception as e:
        response = AnalyzeResponse(job_id=job_id, status="error", error=str(e))
    _jobs[job_id] = response
    return response


@app.post("/analyze/upload", response_model=AnalyzeResponse)
async def analyze_uploaded_video(
    file: UploadFile = File(..., description="Video file to analyze"),
    analysis_types: str = Form("full", description="Comma-separated: keyframes,transcribe,objects,summary,full"),
    frame_interval_sec: float = Form(5.0),
    max_frames: int = Form(20),
    whisper_model: str = Form("base"),
):
    """Analyze an uploaded video file."""
    job_id = str(uuid.uuid4())

    parsed_types: list[AnalysisType] = []
    for t in analysis_types.split(","):
        t = t.strip()
        try:
            parsed_types.append(AnalysisType(t))
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Unknown analysis type: '{t}'")

    try:
        contents = await file.read()
        suffix = Path(file.filename or "video.mp4").suffix or ".mp4"

        request = AnalyzeRequest(
            url=f"upload://{file.filename}",
            analysis_types=parsed_types,
            frame_interval_sec=frame_interval_sec,
            max_frames=max_frames,
            whisper_model=whisper_model,
        )

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, _sync_pipeline_from_bytes, contents, suffix, request
        )
        response = AnalyzeResponse(job_id=job_id, status="completed", result=result)
    except HTTPException:
        raise
    except Exception as e:
        response = AnalyzeResponse(job_id=job_id, status="error", error=str(e))

    _jobs[job_id] = response
    return response


@app.get("/jobs/{job_id}", response_model=AnalyzeResponse)
async def get_job(job_id: str):
    """Retrieve the result of a previous analysis by job ID."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return _jobs[job_id]


@app.get("/jobs")
async def list_jobs():
    """List all job IDs and their statuses."""
    return [{"job_id": jid, "status": j.status} for jid, j in _jobs.items()]


def _sync_pipeline(request: AnalyzeRequest) -> AnalysisResult:
    with tempfile.TemporaryDirectory(prefix="video_tool_api_") as tmpdir:
        tmp = Path(tmpdir)
        src = resolve_source(request.url)
        video_path = download_video(src, tmp / "download")
        return _run_pipeline_on_video(video_path, request.url, request, tmp)


def _sync_pipeline_from_bytes(
    contents: bytes, suffix: str, request: AnalyzeRequest
) -> AnalysisResult:
    with tempfile.TemporaryDirectory(prefix="video_tool_upload_") as tmpdir:
        tmp = Path(tmpdir)
        video_path = tmp / f"upload{suffix}"
        video_path.write_bytes(contents)
        return _run_pipeline_on_video(video_path, request.url, request, tmp)


def _run_pipeline_on_video(
    video_path: Path, source_str: str, request: AnalyzeRequest, tmp: Path
) -> AnalysisResult:
    try:
        duration = get_video_duration(video_path)
    except Exception:
        duration = None

    frames = extract_frames(
        video_path,
        tmp / "frames",
        strategy=request.sampling_strategy,
        interval_sec=request.frame_interval_sec,
        max_frames=request.max_frames,
    )

    transcription = None
    needs_transcription = (
        AnalysisType.TRANSCRIBE in request.analysis_types
        or AnalysisType.FULL in request.analysis_types
    )
    if needs_transcription:
        audio_path = extract_audio(video_path, tmp / "audio.wav")
        if audio_path:
            transcription = transcribe(audio_path, model_name=request.whisper_model)

    return run_analysis(
        frames=frames,
        analysis_types=request.analysis_types,
        source_str=source_str,
        duration_sec=duration,
        transcription=transcription,
    )
