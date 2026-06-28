# Raw Data Lake

Unprocessed input data that feeds the knowledge base. Nothing here is "knowledge" yet —
it's the raw material the LOOP refines into the Wiki (`knowledge/`).

## Folder structure

| Folder | What goes here |
|---|---|
| `_inbox/` | Landing zone — drop any file here, run `brain.py ingest` |
| `conversations/` | AI conversation exports, chat logs |
| `ecosystem/` | Emails, local files, personal documents |
| `goals/` | Life goals, project briefs, OKRs |
| `transcripts/` | Meeting transcripts, interview recordings |
| `feeds/` | Newsletter archives, curated articles, RSS exports |

## Workflow

```
[Source] → raw/_inbox/         # INFLOW: automated pipelines copy here
         → brain.py ingest     # UPLOAD: classify and queue everything
         → brain.py review     # LOOP: approve / reject / flag
         → knowledge/          # BASE: promoted entries live here (the Wiki)
```

## Quick commands

```bash
# Drop a file and process it immediately
cp meeting-notes.txt raw/_inbox/
python brain.py ingest

# Review the queue
python brain.py queue
python brain.py review

# Check overall system state
python brain.py status
```

## Files managed by brain.py

- `_queue.json` — pending review items (3 buckets: auto_approve / need_signoff / need_context)
- `_inflow.json` — configured data pipeline sources
