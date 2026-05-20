from __future__ import annotations

from pathlib import Path
from typing import Optional

import whisper

from .models import TranscriptionResult, TranscriptionSegment, TranscriptionError

_whisper_cache: dict[str, whisper.Whisper] = {}


def load_model(model_name: str = "base") -> whisper.Whisper:
    if model_name not in _whisper_cache:
        _whisper_cache[model_name] = whisper.load_model(model_name)
    return _whisper_cache[model_name]


def transcribe(
    audio_path: Path,
    model_name: str = "base",
    language: Optional[str] = None,
) -> Optional[TranscriptionResult]:
    if not audio_path.exists() or audio_path.stat().st_size == 0:
        return None

    try:
        model = load_model(model_name)
        raw = model.transcribe(
            str(audio_path),
            language=language,
            verbose=False,
            fp16=False,
        )
        return _build_result(raw)
    except Exception as e:
        raise TranscriptionError(f"Whisper transcription failed: {e}") from e


def _build_result(raw: dict) -> TranscriptionResult:
    segments = [
        TranscriptionSegment(
            start=seg["start"],
            end=seg["end"],
            text=seg["text"].strip(),
        )
        for seg in raw.get("segments", [])
    ]
    return TranscriptionResult(
        language=raw.get("language", "unknown"),
        full_text=raw.get("text", "").strip(),
        segments=segments,
    )
