---
title: Preferred project layout
category: architecture
tags: [structure, layout, python, project]
created: 2026-06-28
---

# Preferred Python project layout

## Standard layout used in this repo
```
project-root/
├── CLAUDE.md               # Claude context + project instructions
├── README.md               # User-facing docs
├── requirements.txt        # Pinned dependencies
├── cli.py                  # Typer CLI entrypoint
├── api.py                  # FastAPI server entrypoint
├── knowledge/              # Brain: persistent knowledge base (this system)
│   ├── patterns/           # Reusable code patterns
│   ├── apis/               # API & library notes
│   ├── architecture/       # Design decisions
│   └── domain/             # Business/domain rules
├── <package>/              # Core logic package
│   ├── models.py           # Pydantic data models
│   ├── downloader.py       # I/O / fetching
│   ├── extractor.py        # Processing
│   ├── transcriber.py      # ML / inference
│   └── analyzer.py         # AI integration
└── tests/
    └── integration_test.py
```

## Conventions
- `cli.py` and `api.py` are thin entrypoints — all logic lives in the package
- Models defined in `models.py` are shared between CLI, API, and core logic
- No circular imports: `models.py` imports nothing from the package
- Tests import from the package directly, not from CLI/API entrypoints
