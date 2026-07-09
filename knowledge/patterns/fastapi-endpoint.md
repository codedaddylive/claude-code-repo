---
title: FastAPI endpoint patterns
category: patterns
tags: [fastapi, python, api, routing]
created: 2026-06-28
---

# FastAPI endpoint patterns

## Basic endpoint with Pydantic response model
```python
from fastapi import APIRouter
from video_tool.models import AnalysisResult

router = APIRouter()

@router.get("/items/{item_id}", response_model=AnalysisResult)
async def get_item(item_id: str):
    ...
```

## File upload endpoint
```python
from fastapi import UploadFile, File, BackgroundTasks
import tempfile, shutil

@router.post("/analyze/upload")
async def analyze_upload(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    suffix = Path(file.filename).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    background_tasks.add_task(cleanup, tmp_path)
    ...
```

## Notes
- Always use `response_model=` to get automatic serialization and docs
- Use `BackgroundTasks` for cleanup after response is sent — never block the response
- Prefix routers in `api.py` via `app.include_router(router, prefix="/v1")`
