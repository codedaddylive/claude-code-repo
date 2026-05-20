"""
setup.py — preflight checker and dependency installer for claude-video.

Usage:
    python scripts/setup.py --check     # print dependency status table
    python scripts/setup.py --install   # auto-install via brew (macOS only)
"""

import os
import shutil
import subprocess
import sys

ENV_FILE = os.path.expanduser("~/.config/watch/.env")


def load_env():
    """Read ~/.config/watch/.env and export keys into os.environ."""
    if not os.path.exists(ENV_FILE):
        return
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def check_deps():
    """Return dict of dependency name → (available: bool, path_or_note: str)."""
    results = {}
    for tool in ("ffmpeg", "ffprobe", "yt-dlp"):
        path = shutil.which(tool)
        results[tool] = (path is not None, path or "not found")
    return results


def check_whisper_keys():
    """Return which Whisper API keys are present in the environment."""
    keys = {}
    for var in ("GROQ_API_KEY", "OPENAI_API_KEY"):
        val = os.environ.get(var, "")
        keys[var] = bool(val)
    return keys


def install_deps_macos():
    """Run brew install for missing dependencies. macOS only."""
    if sys.platform != "darwin":
        print("Auto-install is only supported on macOS (brew).", file=sys.stderr)
        sys.exit(1)
    if not shutil.which("brew"):
        print("Homebrew not found. Install from https://brew.sh/", file=sys.stderr)
        sys.exit(1)
    deps = check_deps()
    missing = [name for name, (ok, _) in deps.items() if not ok and name != "ffprobe"]
    if not missing:
        print("All dependencies already installed.")
        return
    # ffprobe ships with ffmpeg
    pkgs = ["ffmpeg" if t == "ffprobe" else t for t in missing]
    pkgs = list(dict.fromkeys(pkgs))
    cmd = ["brew", "install"] + pkgs
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)


def _status(ok):
    return "OK" if ok else "MISSING"


def print_check():
    """Print a human-readable dependency status table."""
    load_env()
    deps = check_deps()
    keys = check_whisper_keys()

    width = 22
    print()
    print("claude-video preflight check")
    print("=" * 40)
    print(f"{'Dependency':<{width}} {'Status':<10} {'Detail'}")
    print("-" * 60)
    for name, (ok, detail) in deps.items():
        status = _status(ok)
        print(f"{name:<{width}} {status:<10} {detail}")
    print()
    print(f"{'API key':<{width}} {'Status'}")
    print("-" * 40)
    for var, present in keys.items():
        status = _status(present)
        note = "(Whisper fallback enabled)" if present else "(optional — needed without native captions)"
        print(f"{var:<{width}} {status:<10} {note}")

    missing_deps = [n for n, (ok, _) in deps.items() if not ok]
    print()
    if missing_deps:
        print(f"Missing required tools: {', '.join(missing_deps)}")
        print("  macOS:  python scripts/setup.py --install")
        print("  Linux:  sudo apt install ffmpeg  &&  pip install yt-dlp")
        sys.exit(1)
    else:
        print("All required dependencies found.")

    if not any(keys.values()):
        print()
        print("No Whisper API keys set. Transcription will only work for")
        print("videos with native captions. Set GROQ_API_KEY in:")
        print(f"  {ENV_FILE}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="claude-video preflight checker")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true", help="Print dependency status")
    group.add_argument("--install", action="store_true", help="Auto-install deps via brew (macOS)")
    args = parser.parse_args()

    if args.install:
        install_deps_macos()
    else:
        print_check()


if __name__ == "__main__":
    main()
