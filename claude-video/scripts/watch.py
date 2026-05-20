"""
watch.py — orchestrator for the claude-video /watch skill.

Usage:
    python scripts/watch.py <url_or_path> [question] [flags]

Output (machine-parseable for Claude Code):
    FRAME:/path/to/frame_000001_t00-00.jpg
    ...
    TRANSCRIPT:
    [00:00] caption text
    ...
    QUESTION: the user's question
"""

import argparse
import os
import sys
import tempfile

# Allow running from any working directory
_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import setup
import download
import frames as frames_mod
import transcribe


def parse_args():
    parser = argparse.ArgumentParser(
        description="Watch a video and answer a question about it.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("url_or_path", help="Video URL or local file path")
    parser.add_argument(
        "question",
        nargs="?",
        default="Describe what happens in this video.",
        help="Question to answer about the video",
    )
    parser.add_argument("--start", metavar="TIME", help="Focus window start (e.g. 1:30, 90)")
    parser.add_argument("--end", metavar="TIME", help="Focus window end")
    parser.add_argument("--max-frames", metavar="N", type=int, help="Override frame budget cap")
    parser.add_argument("--resolution", metavar="W", type=int, default=512,
                        help="Frame width in pixels (default: 512)")
    parser.add_argument("--fps", metavar="F", type=float,
                        help="Override fps (capped at 2.0)")
    parser.add_argument("--whisper", metavar="BACKEND", choices=["groq", "openai"],
                        help="Force Whisper backend")
    parser.add_argument("--no-whisper", action="store_true",
                        help="Disable Whisper transcription fallback")
    parser.add_argument("--out-dir", metavar="DIR",
                        help="Keep working files in this directory")
    parser.add_argument("--no-cleanup", action="store_true",
                        help="Don't suggest removing working directory")
    return parser.parse_args()


def main():
    args = parse_args()

    # Load env vars from ~/.config/watch/.env
    setup.load_env()

    # Verify required tools are available
    deps = setup.check_deps()
    missing = [name for name, (ok, _) in deps.items() if not ok]
    if missing:
        print(
            f"Error: missing required tools: {', '.join(missing)}\n"
            "Run: python scripts/setup.py --check",
            file=sys.stderr,
        )
        sys.exit(1)

    # Resolve start/end times
    start_s = frames_mod.parse_time(args.start) if args.start else None
    end_s = frames_mod.parse_time(args.end) if args.end else None

    # Set up working directory
    tmp_created = False
    if args.out_dir:
        out_dir = os.path.abspath(args.out_dir)
        os.makedirs(out_dir, exist_ok=True)
    else:
        out_dir = tempfile.mkdtemp(prefix="watch_")
        tmp_created = True

    try:
        # Step 1: Acquire video
        if download.is_url(args.url_or_path):
            print(f"Downloading: {args.url_or_path}", flush=True)
            info = download.download_video(args.url_or_path, out_dir, start_s, end_s)
        else:
            path = os.path.expanduser(args.url_or_path)
            print(f"Probing local file: {path}", flush=True)
            duration = download.probe_local(path)
            info = {
                "video_path": path,
                "vtt_path": None,
                "duration": duration,
            }

        duration = info["duration"]
        video_path = info["video_path"]
        vtt_path = info.get("vtt_path")

        print(f"Duration: {duration:.1f}s", flush=True)

        # Step 2: Calculate fps and extract frames
        if args.fps:
            fps = min(args.fps, 2.0)
        else:
            fps = frames_mod.calculate_fps(duration, start_s, end_s, args.max_frames)

        print(f"Extracting frames at {fps:.3f} fps...", flush=True)
        frame_list = frames_mod.extract_frames(
            video_path,
            os.path.join(out_dir, "frames"),
            fps,
            start=start_s,
            end=end_s,
            width=args.resolution,
        )
        print(f"Extracted {len(frame_list)} frames.", flush=True)

        # Step 3: Transcribe
        transcript = transcribe.get_transcript(
            vtt_path,
            video_path,
            out_dir,
            backend=args.whisper,
            no_whisper=args.no_whisper,
        )

        # Step 4: Emit structured output for Claude to parse
        print()
        for frame in frame_list:
            print(f"FRAME:{frame['path']}")

        print()
        print("TRANSCRIPT:")
        print(transcript)

        print()
        print(f"QUESTION: {args.question}")

        if tmp_created and not args.no_cleanup:
            print()
            print(f"# Working files in: {out_dir}")
            print(f"# To clean up: rm -rf {out_dir}")

    except (FileNotFoundError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
