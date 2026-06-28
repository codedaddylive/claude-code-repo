---
title: Pydantic v2 model patterns
category: patterns
tags: [pydantic, python, validation, models]
created: 2026-06-28
---

# Pydantic v2 model patterns

## Base model with validation
```python
from pydantic import BaseModel, Field, model_validator
from typing import Optional, List
from enum import Enum

class Status(str, Enum):
    pending = "pending"
    done = "done"
    failed = "failed"

class JobInput(BaseModel):
    url: str = Field(..., description="Video URL or local path")
    max_frames: int = Field(5, ge=1, le=50)
    status: Status = Status.pending

    @model_validator(mode="after")
    def check_url_or_path(self) -> "JobInput":
        if not self.url:
            raise ValueError("url must not be empty")
        return self
```

## Nested result model
```python
class FrameDescription(BaseModel):
    timestamp: float
    description: str
    objects: List[str] = Field(default_factory=list)

class AnalysisResult(BaseModel):
    job_id: str
    frames: List[FrameDescription] = Field(default_factory=list)
    transcript: Optional[str] = None
    summary: Optional[str] = None
```

## Notes
- Use `Field(default_factory=list)` not `Field(default=[])` to avoid shared mutable default
- Pydantic v2: validators are `@model_validator` / `@field_validator` (not `@validator`)
- `model.model_dump()` replaces v1's `model.dict()`
- `model.model_dump_json()` for JSON string output
