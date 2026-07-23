# Aria for VS Code

A standalone VS Code extension that talks to a local **Aria** server — ask
questions over your GitHub repositories with cited answers, powered by
open-source models. It runs entirely on its own and does **not** depend on
Claude Code or any other assistant.

```
VS Code (this extension)  ──HTTP──►  Aria API server  ──►  open-source model
                                     (uvicorn aria.api)      (Ollama or hosted)
```

## What it adds (Command Palette → "Aria: …")

| Command | Does |
|---|---|
| **Aria: Start Local Server** | Launches `uvicorn aria.api:app` in a terminal |
| **Aria: Index Workspace Folder(s)** | Ingests your open folder(s) into Aria |
| **Aria: Index a GitHub Repo…** | Ingests any `owner/repo`, URL, or path |
| **Aria: Open Chat** | Chat panel with answers + clickable source citations |
| **Aria: Ask a Question…** | Quick one-off question |
| **Aria: Recommend AI Team** | Shows the open-source model roster (LLM-as-a-judge) |
| **Aria: Check Server Health** | Verifies the server + indexed chunk count |

Clicking a source in the chat opens that file at the cited line (for
workspace-indexed repos).

## Prerequisites

1. **Python + Aria installed** (from the repo root):
   ```bash
   pip install -r aria/requirements.txt
   ```
2. **A model backend.** Either local Ollama (`ollama pull llama3.1:8b` +
   `ollama pull nomic-embed-text`), or a hosted provider — set the `ARIA_*`
   env vars before starting the server. Fully offline mode also works:
   `export ARIA_LLM_BACKEND=echo ARIA_EMBED_BACKEND=hash`.

## Install the extension

**Option A — run from source (fastest):**
1. Open the `aria/vscode/` folder in VS Code.
2. Press **F5** ("Run Extension") — a second VS Code window opens with Aria loaded.

**Option B — package and install:**
```bash
npm install -g @vscode/vsce
cd aria/vscode
vsce package                       # produces aria-vscode-0.1.0.vsix
code --install-extension aria-vscode-0.1.0.vsix
```

There is no build step — the extension is plain JavaScript.

## Use it

1. **Start the server**: run **Aria: Start Local Server** (or run
   `uvicorn aria.api:app --port 8100 --workers 1` yourself, with your `ARIA_*`
   env vars set in that terminal).
2. **Index code**: open your project and run **Aria: Index Workspace Folder(s)**.
3. **Ask**: run **Aria: Open Chat** and ask away — answers cite the files used.

## Settings

| Setting | Default | Description |
|---|---|---|
| `aria.apiUrl` | `http://localhost:8100` | URL of the running Aria server |
| `aria.pythonPath` | `python` | Interpreter used by "Start Local Server" |

Point `aria.apiUrl` at a remote Aria deployment (see `../DEPLOY.md`) to use a
shared server instead of a local one.
