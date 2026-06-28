---
title: Video analysis domain concepts
category: domain
tags: [video, analysis, domain, concepts]
created: 2026-06-28
---

# Video analysis domain concepts

## Core terms
- **Keyframe**: a representative frame extracted at regular intervals or scene changes; used for visual analysis instead of every frame
- **Scene change detection**: detecting when the visual content changes significantly (OpenCV frame diff threshold); more semantically meaningful than fixed-interval extraction
- **Transcript**: full speech-to-text of the audio track, produced by Whisper
- **Visual summary**: Claude's high-level description of the video content derived from keyframe descriptions

## Frame extraction strategies
| Strategy | When to use | Config |
|---|---|---|
| Fixed interval | Regular content, known duration | `--interval 5` (seconds) |
| Max frames | Unknown duration, want coverage | `--max-frames 10` |
| Scene change | Narrative/event content | threshold-based, OpenCV |

## Output structure
- `frames`: list of {timestamp, description, objects_detected}
- `transcript`: full text of speech
- `summary`: Claude's synthesis across all frames + transcript
- `metadata`: duration, resolution, fps, source URL

## Quality considerations
- More frames = better coverage but higher API cost and latency
- `base` Whisper model sufficient for clear speech; use `medium`/`large` for accented or noisy audio
- Claude vision performs best on frames with clear subjects; blurry or dark frames yield vague descriptions
