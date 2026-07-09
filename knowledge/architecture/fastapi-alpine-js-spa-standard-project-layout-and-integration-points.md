---
title: FastAPI + Alpine.js SPA: standard project layout and integration points
category: architecture
tags: [fastapi, alpine.js, spa, layout, httponly-cookie, auth, jinja2]
created: 2026-07-06
---

# FastAPI + Alpine.js SPA: standard project layout and integration points

## Stack
FastAPI backend + single-file Alpine.js SPA frontend. No build step, no bundler. Frontend served as static files from FastAPI.

## Directory layout
```
project/
├── backend/
│   ├── .venv/              # Python venv (3.11)
│   ├── main.py             # FastAPI app, mounts /static, serves index.html fallback
│   ├── models.py           # SQLAlchemy models
│   ├── database.py         # DB init (pysqlite3-binary override must be FIRST import on RHEL 9)
│   ├── routes/             # One file per domain (auth.py, export.py, etc.)
│   └── services/           # Business logic (vector_store.py, bedrock_client.py, etc.)
├── frontend/
│   ├── index.html          # Entire SPA — Alpine components inline, no build step
│   └── static/
│       ├── style.css       # Global CSS (includes * { margin:0; padding:0 } reset — see padding note)
│       └── *.png / *.js    # Assets
├── certs/                  # Self-signed TLS (cert.pem, key.pem)
├── tests/
│   ├── test_frontend_lint.py  # Static HTML checks (no server needed)
│   └── ...
├── start.sh                # Starts uvicorn with SSL
├── stop.sh
└── server.pid              # WARNING: can go stale — use ss -ltnp | grep <port> to find real PID
```

## Auth pattern
- httpOnly cookie (qa_session), 2h sliding JWT
- All /api/* routes gated except /api/auth/*
- Login: POST /api/auth/login → sets cookie
- Test user: no MFA; admin: MFA enabled (don't use in automation)

## CSS global reset gotcha
```css
* { margin: 0; padding: 0; }  /* resets all intrinsic heading/paragraph spacing */
```
This means h1-h4 and p inside a bare .card have ZERO gap to the card border. Any .card that contains bare headings needs an explicit padding class (e.g. rb-card-pad { padding: 1.25rem }).

## Server restart
```bash
# server.pid goes stale — always find the real PID
ss -ltnp | grep 5173
kill <real-pid>
bash start.sh
```

## RHEL 9 SQLite override
SQLite 3.34 ships with RHEL 9; ChromaDB/SQLAlchemy need 3.35+. Fix:
```python
# database.py — must be first import, before sqlalchemy
import pysqlite3
import sys
sys.modules['sqlite3'] = pysqlite3
```
