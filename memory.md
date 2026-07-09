# Memory — Persistent Preference Log

> Claude appends new rules to this file as preferences are discovered or corrected.
> These rules override defaults. Read this every session.

---

## Core Rules (always active)

### Communication
- No emojis unless explicitly asked
- No multi-paragraph explanations before code — code first, one-line context after if needed
- Short in-progress updates (one sentence), not running commentary
- End-of-turn summary: one or two sentences max — what changed, what's next

### Code generation
- No comments unless the WHY is non-obvious
- No docstrings longer than one line
- No backwards-compat shims for removed code — delete cleanly
- No feature flags or abstractions for hypothetical future requirements
- Validate only at system boundaries (user input, external APIs) — trust internal code
- Default to no error handling for scenarios that can't happen

### Files & structure
- Prefer editing existing files over creating new ones
- Never create README or documentation files unless explicitly asked
- Temp files go in the scratchpad directory, never `/tmp`

### Git & GitHub
- Always branch — never commit directly to main
- Confirm before any destructive git operation
- Push + open draft PR after every significant commit
- Never skip hooks (`--no-verify`) — fix the underlying issue instead

### ARIA (check before implementing)
- Always run `python brain.py search <topic>` before writing new code
- If a knowledge entry covers it, follow that pattern
- After settling a new decision, add it: `python brain.py add --title "..." --category <cat>`

### Multi-agent (Squad)
- Use `/squad` to delegate parallel or independent work
- Manager always checks ARIA before briefing workers
- Workers reference which knowledge entries they consulted

---

## Appended Rules

> Claude adds new entries here during sessions when preferences are clarified or corrected.
> Format: `[YYYY-MM-DD] Rule — source/reason`

- [2026-06-29] Use `imageio-ffmpeg` binary (not system ffmpeg) for any H.264/MP4 encoding — system ffmpeg is VP8-only
- [2026-06-29] iOS video must be MP4/H.264 — WebM/VP8 renders black screen on iPhone
- [2026-06-29] Remotion needs `chromium_headless_shell` binary, not regular Chrome — old headless mode was removed from standard Chromium
- [2026-06-29] ffmpeg `image2pipe` demuxer requires explicit `-vcodec mjpeg` before `-i pipe:0` when piping JPEGs
- [2026-06-29] Squad is from `github.com/mco-org/squad` — SQLite-based, not cloud-dependent
- [2026-07-04] Run the `llm-council` skill PROACTIVELY (without being asked) before any consequential AND hard-to-reverse decision (dependency/architecture/API/vendor/feature commit). Judge must be a SEPARATE agent/fresh context — never self-grade. Routine/reversible work stays "recommend, don't over-plan".
- [2026-07-07] Before judging a factual/research claim as false or confabulated, CROSS-REFERENCE with WebSearch to validate. WebSearch routes through Anthropic's backend and works even when direct WebFetch is blocked by the network policy. Don't rely on training-memory skepticism alone — verify, then conclude. (Learned after wrongly suspecting Anthropic's real "J-space" research was confabulated.)
