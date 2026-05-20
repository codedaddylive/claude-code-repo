from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Optional

import anthropic

from .models import (
    AnalysisError,
    AnalysisResult,
    AnalysisType,
    FrameInfo,
    ObjectDetectionResult,
    TranscriptionResult,
)

MODEL = "claude-sonnet-4-6"
MAX_FRAMES_PER_CALL = 10


def get_client() -> anthropic.Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY environment variable is not set.")
    return anthropic.Anthropic(api_key=api_key)


def encode_frame(frame: FrameInfo) -> FrameInfo:
    with open(frame.file_path, "rb") as fh:
        frame.base64_data = base64.standard_b64encode(fh.read()).decode("utf-8")
    return frame


def analyze_keyframes(
    client: anthropic.Anthropic,
    frames: list[FrameInfo],
) -> list[str]:
    descriptions: list[str] = []
    for batch in _batched(frames, MAX_FRAMES_PER_CALL):
        content = _build_image_blocks(batch)
        content.append({
            "type": "text",
            "text": (
                "For each frame shown above (in order), provide a single concise sentence "
                "describing what is visible. Number each description matching the frame label "
                "(e.g. 'Frame 0: ...'). One sentence per frame, nothing else."
            ),
        })
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=1024,
                messages=[{"role": "user", "content": content}],
            )
            text = response.content[0].text
            descriptions.extend(_parse_numbered_lines(text, len(batch)))
        except anthropic.APIError as e:
            raise AnalysisError(f"Claude API error during keyframe analysis: {e}") from e
    return descriptions


def detect_objects_and_scenes(
    client: anthropic.Anthropic,
    frames: list[FrameInfo],
) -> list[ObjectDetectionResult]:
    results: list[ObjectDetectionResult] = []
    for batch in _batched(frames, MAX_FRAMES_PER_CALL):
        content = _build_image_blocks(batch)
        content.append({
            "type": "text",
            "text": (
                "For each frame shown above, identify the objects present and describe the scene. "
                "Respond ONLY with a JSON array in this exact format, no other text:\n"
                '[\n'
                '  {"frame_index": 0, "objects": ["obj1", "obj2"], "scene": "description"},\n'
                '  ...\n'
                ']'
            ),
        })
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=2048,
                messages=[{"role": "user", "content": content}],
            )
            raw_text = response.content[0].text.strip()
            parsed = _parse_json_array(raw_text)
            for item, frame in zip(parsed, batch):
                results.append(ObjectDetectionResult(
                    frame_index=frame.index,
                    timestamp_sec=frame.timestamp_sec,
                    detected_objects=item.get("objects", []),
                    scene_description=item.get("scene", ""),
                ))
        except anthropic.APIError as e:
            raise AnalysisError(f"Claude API error during object detection: {e}") from e
    return results


def generate_visual_summary(
    client: anthropic.Anthropic,
    frames: list[FrameInfo],
    transcription: Optional[TranscriptionResult] = None,
) -> str:
    # Use at most MAX_FRAMES_PER_CALL representative frames spread evenly
    step = max(1, len(frames) // MAX_FRAMES_PER_CALL)
    sampled = frames[::step][:MAX_FRAMES_PER_CALL]

    transcript_context = ""
    if transcription and transcription.full_text:
        transcript_context = f"\n\nAudio transcript:\n{transcription.full_text}\n"

    content = _build_image_blocks(sampled)
    content.append({
        "type": "text",
        "text": (
            f"You are analyzing a video.{transcript_context}\n"
            f"Here are {len(sampled)} frames sampled throughout the video. "
            "Provide a comprehensive summary covering: the main subject or topic, "
            "key events or actions, setting or environment, and any notable details. "
            "Write 2-3 paragraphs in plain prose."
        ),
    })

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": content}],
        )
        return response.content[0].text.strip()
    except anthropic.APIError as e:
        raise AnalysisError(f"Claude API error during summary generation: {e}") from e


def run_analysis(
    frames: list[FrameInfo],
    analysis_types: list[AnalysisType],
    source_str: str,
    duration_sec: Optional[float],
    transcription: Optional[TranscriptionResult] = None,
) -> AnalysisResult:
    do_all = AnalysisType.FULL in analysis_types
    client = get_client()

    encoded = [encode_frame(f) for f in frames]

    result = AnalysisResult(
        source=source_str,
        duration_sec=duration_sec,
        frame_count=len(encoded),
        transcription=transcription,
    )

    if do_all or AnalysisType.KEYFRAMES in analysis_types:
        result.keyframe_descriptions = analyze_keyframes(client, encoded)

    if do_all or AnalysisType.OBJECTS in analysis_types:
        result.object_detections = detect_objects_and_scenes(client, encoded)

    if do_all or AnalysisType.SUMMARY in analysis_types:
        result.visual_summary = generate_visual_summary(client, encoded, transcription)

    return result


# ── helpers ──────────────────────────────────────────────────────────────────

def _build_image_blocks(frames: list[FrameInfo]) -> list[dict]:
    content: list[dict] = []
    for frame in frames:
        content.append({"type": "text", "text": f"Frame {frame.index} at {frame.timestamp_sec:.1f}s:"})
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": frame.base64_data,
            },
        })
    return content


def _batched(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _parse_numbered_lines(text: str, expected: int) -> list[str]:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    descriptions: list[str] = []
    for line in lines:
        # Strip leading "Frame N: " prefix if present
        cleaned = line.split(":", 1)[-1].strip() if ":" in line else line
        descriptions.append(cleaned)
    # Pad or trim to match expected count
    while len(descriptions) < expected:
        descriptions.append("")
    return descriptions[:expected]


def _parse_json_array(text: str) -> list[dict]:
    # Extract JSON array even if Claude adds surrounding text
    start = text.find("[")
    end = text.rfind("]") + 1
    if start == -1 or end == 0:
        return []
    try:
        return json.loads(text[start:end])
    except json.JSONDecodeError:
        return []
