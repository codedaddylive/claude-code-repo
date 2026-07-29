// Aria VS Code extension — a standalone client for a local Aria API server.
// Plain CommonJS (no build step). Talks HTTP to `uvicorn aria.api:app`.
const vscode = require("vscode");
const http = require("http");
const https = require("https");
const { URL } = require("url");

/** @returns {string} configured API base URL, no trailing slash */
function apiUrl() {
  return String(vscode.workspace.getConfiguration("aria").get("apiUrl") || "http://localhost:8100").replace(/\/$/, "");
}

/**
 * Minimal JSON HTTP request against the Aria server.
 * @returns {Promise<any>}
 */
function apiRequest(method, path, body) {
  return new Promise((resolve, reject) => {
    let target;
    try {
      target = new URL(apiUrl() + path);
    } catch (e) {
      return reject(new Error("Invalid aria.apiUrl setting: " + e.message));
    }
    const payload = body ? Buffer.from(JSON.stringify(body)) : null;
    const lib = target.protocol === "https:" ? https : http;
    const req = lib.request(
      target,
      {
        method,
        headers: Object.assign(
          { Accept: "application/json" },
          payload ? { "Content-Type": "application/json", "Content-Length": payload.length } : {}
        ),
        timeout: 600000,
      },
      (res) => {
        let data = "";
        res.on("data", (c) => (data += c));
        res.on("end", () => {
          let parsed = null;
          try {
            parsed = data ? JSON.parse(data) : null;
          } catch (_) {
            /* non-JSON */
          }
          if (res.statusCode && res.statusCode >= 200 && res.statusCode < 300) {
            resolve(parsed);
          } else {
            const detail = parsed && parsed.detail ? parsed.detail : data || res.statusMessage;
            reject(new Error(`Aria server ${res.statusCode}: ${detail}`));
          }
        });
      }
    );
    req.on("timeout", () => req.destroy(new Error("Request timed out")));
    req.on("error", (e) =>
      reject(new Error(`Cannot reach Aria at ${apiUrl()} (${e.message}). Start it with “Aria: Start Local Server”.`))
    );
    if (payload) req.write(payload);
    req.end();
  });
}

// --------------------------------------------------------------------------- //
// Commands
// --------------------------------------------------------------------------- //
async function checkHealth() {
  try {
    const h = await apiRequest("GET", "/health");
    vscode.window.showInformationMessage(`Aria OK — ${h.indexed_chunks} chunks indexed at ${apiUrl()}.`);
  } catch (e) {
    vscode.window.showErrorMessage(e.message);
  }
}

async function ingestWorkspace() {
  const folders = vscode.workspace.workspaceFolders;
  if (!folders || folders.length === 0) {
    vscode.window.showWarningMessage("Open a folder first, then run “Aria: Index Workspace Folder(s)”.");
    return;
  }
  await vscode.window.withProgress(
    { location: vscode.ProgressLocation.Notification, title: "Aria: indexing workspace", cancellable: false },
    async (progress) => {
      for (const f of folders) {
        progress.report({ message: f.name });
        try {
          const stats = await apiRequest("POST", "/ingest", { source: f.uri.fsPath });
          vscode.window.showInformationMessage(`Indexed ${stats.repo}: ${stats.files} files, ${stats.chunks} chunks.`);
        } catch (e) {
          vscode.window.showErrorMessage(e.message);
        }
      }
    }
  );
}

async function ingestRepo() {
  const source = await vscode.window.showInputBox({
    prompt: "GitHub repo to index (owner/repo, URL, or local path)",
    placeHolder: "pallets/flask",
  });
  if (!source) return;
  await vscode.window.withProgress(
    { location: vscode.ProgressLocation.Notification, title: `Aria: indexing ${source}`, cancellable: false },
    async () => {
      try {
        const stats = await apiRequest("POST", "/ingest", { source });
        vscode.window.showInformationMessage(`Indexed ${stats.repo}: ${stats.files} files, ${stats.chunks} chunks.`);
      } catch (e) {
        vscode.window.showErrorMessage(e.message);
      }
    }
  );
}

async function askQuick() {
  const question = await vscode.window.showInputBox({ prompt: "Ask Aria about your indexed repositories" });
  if (!question) return;
  const panel = ChatPanel.show(currentContext);
  panel.ask(question);
}

async function startServer() {
  const cfg = vscode.workspace.getConfiguration("aria");
  const python = String(cfg.get("pythonPath") || "python");
  let port = 8100;
  try {
    port = Number(new URL(apiUrl()).port) || 8100;
  } catch (_) {}
  const term = vscode.window.createTerminal("Aria server");
  term.show();
  term.sendText(`${python} -m uvicorn aria.api:app --host 127.0.0.1 --port ${port} --workers 1`);
  vscode.window.showInformationMessage(
    "Starting Aria server in a terminal. Set ARIA_* env vars there for your model backend."
  );
}

// --------------------------------------------------------------------------- //
// Chat webview
// --------------------------------------------------------------------------- //
let currentContext = null;

class ChatPanel {
  static current = null;

  static show(context) {
    const column = vscode.ViewColumn.Beside;
    if (ChatPanel.current) {
      ChatPanel.current.panel.reveal(column);
      return ChatPanel.current;
    }
    const panel = vscode.window.createWebviewPanel("ariaChat", "Aria", column, {
      enableScripts: true,
      retainContextWhenHidden: true,
    });
    ChatPanel.current = new ChatPanel(panel, context);
    return ChatPanel.current;
  }

  constructor(panel, context) {
    this.panel = panel;
    this.panel.webview.html = renderHtml(this.panel.webview);
    this.panel.onDidDispose(() => (ChatPanel.current = null));
    this.panel.webview.onDidReceiveMessage((msg) => {
      if (msg.type === "ask") this.ask(msg.text);
      else if (msg.type === "open") openCitation(msg.citation);
    });
  }

  async ask(question) {
    this.panel.webview.postMessage({ type: "user", text: question });
    this.panel.webview.postMessage({ type: "thinking" });
    try {
      const res = await apiRequest("POST", "/ask", { question });
      const sources = (res.sources || []).map((s) => ({
        citation: s.chunk ? s.chunk.citation : "",
        score: s.score,
      }));
      this.panel.webview.postMessage({ type: "answer", text: res.answer || "", sources });
    } catch (e) {
      this.panel.webview.postMessage({ type: "error", text: e.message });
    }
  }
}

/** Open a `repo/path:start-end` citation in a workspace file, best-effort. */
async function openCitation(citation) {
  const m = /^(.*?)\/(.+):(\d+)-(\d+)$/.exec(citation || "");
  if (!m) return;
  const [, repo, relPath, startStr] = m;
  const start = Math.max(0, parseInt(startStr, 10) - 1);
  const folders = vscode.workspace.workspaceFolders || [];
  const folder = folders.find((f) => f.name === repo) || folders[0];
  if (!folder) {
    vscode.window.showWarningMessage(`Source ${citation} is not in this workspace.`);
    return;
  }
  const fileUri = vscode.Uri.joinPath(folder.uri, relPath);
  try {
    const doc = await vscode.workspace.openTextDocument(fileUri);
    const editor = await vscode.window.showTextDocument(doc, { preview: true });
    const pos = new vscode.Position(start, 0);
    editor.selection = new vscode.Selection(pos, pos);
    editor.revealRange(new vscode.Range(pos, pos), vscode.TextEditorRevealType.InCenter);
  } catch (_) {
    vscode.window.showWarningMessage(`Couldn't open ${relPath} in ${folder.name}.`);
  }
}

async function recommendTeam() {
  await vscode.window.withProgress(
    { location: vscode.ProgressLocation.Notification, title: "Aria: judging AI team", cancellable: false },
    async () => {
      try {
        const roster = await apiRequest("GET", "/team/recommend?method=auto");
        TeamPanel.show(roster);
      } catch (e) {
        vscode.window.showErrorMessage(e.message);
      }
    }
  );
}

class TeamPanel {
  static show(roster) {
    const panel = vscode.window.createWebviewPanel("ariaTeam", "Aria — AI team", vscode.ViewColumn.Active, {
      enableScripts: false,
    });
    panel.webview.html = renderTeamHtml(roster);
  }
}

// --------------------------------------------------------------------------- //
// HTML (theme-aware, CSP-locked)
// --------------------------------------------------------------------------- //
function nonce() {
  let s = "";
  const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  for (let i = 0; i < 24; i++) s += chars.charAt(Math.floor(Math.random() * chars.length));
  return s;
}

function esc(str) {
  return String(str).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function renderHtml(webview) {
  const n = nonce();
  return `<!DOCTYPE html><html><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'nonce-${n}'; script-src 'nonce-${n}';">
<style nonce="${n}">
  body { font-family: var(--vscode-font-family); color: var(--vscode-foreground); margin: 0; padding: 0; }
  #log { padding: 10px; overflow-y: auto; }
  .msg { margin: 8px 0; padding: 8px 10px; border-radius: 6px; white-space: pre-wrap; }
  .user { background: var(--vscode-textBlockQuote-background); }
  .aria { background: var(--vscode-editor-inactiveSelectionBackground); }
  .err { color: var(--vscode-errorForeground); }
  .sources { margin-top: 6px; font-size: 12px; opacity: 0.85; }
  .src { cursor: pointer; text-decoration: underline; color: var(--vscode-textLink-foreground); display: block; }
  #bar { position: sticky; bottom: 0; display: flex; gap: 6px; padding: 8px; background: var(--vscode-editor-background); border-top: 1px solid var(--vscode-panel-border); }
  #q { flex: 1; padding: 6px; background: var(--vscode-input-background); color: var(--vscode-input-foreground); border: 1px solid var(--vscode-input-border); }
  button { padding: 6px 12px; background: var(--vscode-button-background); color: var(--vscode-button-foreground); border: none; cursor: pointer; }
</style></head>
<body>
  <div id="log"></div>
  <div id="bar"><input id="q" placeholder="Ask about your indexed repos…" /><button id="send">Ask</button></div>
<script nonce="${n}">
  const vscode = acquireVsCodeApi();
  const log = document.getElementById('log');
  const q = document.getElementById('q');
  let thinkingEl = null;
  function add(cls, text) { const d = document.createElement('div'); d.className = 'msg ' + cls; d.textContent = text; log.appendChild(d); log.scrollTop = log.scrollHeight; return d; }
  function send() { const t = q.value.trim(); if (!t) return; vscode.postMessage({ type: 'ask', text: t }); q.value = ''; }
  document.getElementById('send').addEventListener('click', send);
  q.addEventListener('keydown', (e) => { if (e.key === 'Enter') send(); });
  window.addEventListener('message', (ev) => {
    const m = ev.data;
    if (m.type === 'user') add('user', m.text);
    else if (m.type === 'thinking') { thinkingEl = add('aria', '…'); }
    else if (m.type === 'error') { if (thinkingEl) { thinkingEl.remove(); thinkingEl = null; } add('aria err', m.text); }
    else if (m.type === 'answer') {
      if (thinkingEl) { thinkingEl.remove(); thinkingEl = null; }
      const d = add('aria', m.text || '(no answer)');
      if (m.sources && m.sources.length) {
        const s = document.createElement('div'); s.className = 'sources'; s.textContent = 'Sources:';
        m.sources.forEach((src) => {
          const a = document.createElement('span'); a.className = 'src';
          a.textContent = src.citation + '  (' + (src.score != null ? src.score.toFixed(3) : '') + ')';
          a.addEventListener('click', () => vscode.postMessage({ type: 'open', citation: src.citation }));
          s.appendChild(a);
        });
        d.appendChild(s);
      }
    }
  });
</script></body></html>`;
}

function renderTeamHtml(roster) {
  const n = nonce();
  const rows = (roster.picks || [])
    .map((p) => {
      const runners = (p.runners_up || []).map((c) => `${esc(c.name)} (${c.score})`).join(", ");
      const run = p.run && (p.run.local || p.run.hosted) ? esc(p.run.local || p.run.hosted) : esc((p.run && p.run.notes) || "");
      return `<tr><td>${esc(p.role_name)}</td><td><b>${esc(p.winner_name)}</b></td><td>${esc(p.score)}</td><td>${esc(p.license)}</td><td><code>${run}</code></td><td>${runners}</td></tr>`;
    })
    .join("");
  return `<!DOCTYPE html><html><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'nonce-${n}';">
<style nonce="${n}">
  body { font-family: var(--vscode-font-family); color: var(--vscode-foreground); padding: 12px; }
  table { border-collapse: collapse; width: 100%; }
  th, td { text-align: left; padding: 6px 10px; border-bottom: 1px solid var(--vscode-panel-border); vertical-align: top; }
  code { font-family: var(--vscode-editor-font-family); font-size: 12px; }
  caption { text-align: left; opacity: 0.8; margin-bottom: 8px; }
</style></head><body>
  <h2>Aria AI team — free &amp; open-source</h2>
  <p>Judge: ${esc(roster.method)}. Ratings are qualitative — verify on live leaderboards.</p>
  <table>
    <tr><th>Role</th><th>Pick</th><th>Score</th><th>License</th><th>Run</th><th>Runners-up</th></tr>
    ${rows}
  </table>
</body></html>`;
}

// --------------------------------------------------------------------------- //
function activate(context) {
  currentContext = context;
  context.subscriptions.push(
    vscode.commands.registerCommand("aria.checkHealth", checkHealth),
    vscode.commands.registerCommand("aria.ingestWorkspace", ingestWorkspace),
    vscode.commands.registerCommand("aria.ingestRepo", ingestRepo),
    vscode.commands.registerCommand("aria.ask", askQuick),
    vscode.commands.registerCommand("aria.openChat", () => ChatPanel.show(context)),
    vscode.commands.registerCommand("aria.team", recommendTeam),
    vscode.commands.registerCommand("aria.startServer", startServer)
  );
}

function deactivate() {}

module.exports = { activate, deactivate };
