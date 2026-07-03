from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict


class AnalysisType(str, Enum):
    KEYFRAMES = "keyframes"
    TRANSCRIBE = "transcribe"
    OBJECTS = "objects"
    SUMMARY = "summary"
    FULL = "full"


class FrameSamplingStrategy(str, Enum):
    INTERVAL = "interval"
    SCENE = "scene"


class VideoSource(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    raw: str
    is_local: bool = False
    local_path: Optional[Path] = None


class FrameInfo(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    index: int
    timestamp_sec: float
    file_path: str
    base64_data: Optional[str] = None


class TranscriptionSegment(BaseModel):
    start: float
    end: float
    text: str


class TranscriptionResult(BaseModel):
    language: str
    full_text: str
    segments: list[TranscriptionSegment]


class ObjectDetectionResult(BaseModel):
    frame_index: int
    timestamp_sec: float
    detected_objects: list[str]
    scene_description: str


class AnalysisResult(BaseModel):
    source: str
    duration_sec: Optional[float] = None
    frame_count: int = 0
    keyframe_descriptions: list[str] = []
    transcription: Optional[TranscriptionResult] = None
    object_detections: list[ObjectDetectionResult] = []
    visual_summary: Optional[str] = None
    raw_claude_responses: list[str] = []


class ViabilityVerdict(str, Enum):
    ADOPT = "adopt"
    INVESTIGATE = "investigate"
    SKIP = "skip"


class ViabilityAssessment(BaseModel):
    source: str
    verdict: ViabilityVerdict
    confidence: float
    reasoning: str
    relevant_to_stack: list[str] = []
    suggested_category: Optional[str] = None
    suggested_title: Optional[str] = None


class AnalyzeRequest(BaseModel):
    url: str
    analysis_types: list[AnalysisType] = [AnalysisType.FULL]
    frame_interval_sec: float = 5.0
    sampling_strategy: FrameSamplingStrategy = FrameSamplingStrategy.INTERVAL
    max_frames: int = 20
    whisper_model: str = "base"


class AnalyzeResponse(BaseModel):
    job_id: str
    status: str
    result: Optional[AnalysisResult] = None
    error: Optional[str] = None


class DownloadError(Exception):
    pass


class ExtractionError(Exception):
    pass


class TranscriptionError(Exception):
    pass


class AnalysisError(Exception):
    pass
