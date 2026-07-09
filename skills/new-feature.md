# Workflow: New Feature

**Trigger**: Adding a new FastAPI endpoint, CLI command, or pipeline module.

---

## Steps

### 1. Check ARIA first

```bash
python brain.py search "<feature topic>"
python brain.py list --category patterns
```

Read any relevant entries before writing a line of code. The patterns in `knowledge/patterns/` are the source of truth for how things are structured here.

Key entries to check:
- `knowledge/patterns/fastapi-endpoint.md` — for new API routes
- `knowledge/patterns/cli-typer.md` — for new CLI commands
- `knowledge/patterns/pydantic-models.md` — for new data models
- `knowledge/architecture/video-pipeline.md` — for pipeline changes

### 2. Define the Pydantic model first

All new I/O crosses through `video_tool/models.py`. Add request/response models there before touching any logic.

```python
# video_tool/models.py
class MyFeatureRequest(BaseModel):
    field: str
    optional_field: int = 0

class MyFeatureResult(BaseModel):
    output: str
    metadata: dict[str, str] = {}
```

### 3. Implement the logic

- Keep functions under ~40 lines — split if longer
- No comments unless the WHY is non-obvious
- Validate only at system boundaries — trust internal code
- Functional style — prefer pure functions over stateful classes

### 4. Wire up the endpoint or CLI command

**FastAPI endpoint** (`api.py`):
```python
@app.post("/my-feature", response_model=MyFeatureResult)
async def my_feature(req: MyFeatureRequest) -> MyFeatureResult:
    ...
```

**Typer CLI command** (`cli.py`):
```python
@app.command()
def my_feature(input: str, output: Path = Path("result.json")):
    ...
```

### 5. Verify it works

```bash
# CLI
python cli.py my-feature "test input"

# API
uvicorn api:app --port 8000 &
curl -X POST http://localhost:8000/my-feature -H "Content-Type: application/json" -d '{"field": "test"}'
```

### 6. Commit and open PR

```bash
git add <changed files>
git commit -m "Add <feature name>"
git push -u origin <branch>
# PR is created automatically
```

### 7. Add to ARIA if a new pattern was settled

```bash
# If this feature introduced a pattern worth reusing
python brain.py add --title "..." --category patterns
python brain.py rebuild-index
# Update CLAUDE.md index
```

---

## Checklist

- [ ] Checked ARIA for existing patterns before starting
- [ ] Pydantic model defined in `models.py`
- [ ] Function stays under ~40 lines
- [ ] No unnecessary comments
- [ ] Manually verified the happy path
- [ ] Committed with descriptive message
- [ ] New pattern added to ARIA (if applicable)

---

## Invocation Example

```
Follow skills/new-feature.md — add a POST /summarize endpoint that takes a video URL and returns a one-paragraph summary.
```
