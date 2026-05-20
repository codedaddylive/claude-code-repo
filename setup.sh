#!/usr/bin/env bash
# setup.sh — one-shot installer for the claude-video /watch skill

set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DEST="$HOME/.claude/skills/watch"

echo ""
echo "claude-video setup"
echo "=================="

# 1. Install system dependencies
echo ""
echo "[1/3] Checking system dependencies..."

install_deps() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        if ! command -v brew &>/dev/null; then
            echo "Homebrew not found. Install from https://brew.sh/ then re-run."
            exit 1
        fi
        MISSING=()
        command -v ffmpeg &>/dev/null || MISSING+=("ffmpeg")
        command -v yt-dlp &>/dev/null || MISSING+=("yt-dlp")
        if [ ${#MISSING[@]} -gt 0 ]; then
            echo "Installing: ${MISSING[*]}"
            brew install "${MISSING[@]}"
        else
            echo "ffmpeg and yt-dlp already installed."
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        MISSING=()
        command -v ffmpeg &>/dev/null || MISSING+=("ffmpeg")
        if [ ${#MISSING[@]} -gt 0 ]; then
            echo "Installing ffmpeg..."
            sudo apt-get install -y ffmpeg
        fi
        command -v yt-dlp &>/dev/null || pip install yt-dlp
    else
        echo "Windows detected — install ffmpeg and yt-dlp manually:"
        echo "  winget install ffmpeg"
        echo "  pip install yt-dlp"
    fi
}

install_deps

# 2. Install the skill
echo ""
echo "[2/3] Installing /watch skill to $SKILL_DEST..."
mkdir -p "$HOME/.claude/skills"
rm -rf "$SKILL_DEST"
cp -r "$REPO_DIR/claude-video" "$SKILL_DEST"
echo "Skill installed."

# 3. Run preflight check
echo ""
echo "[3/3] Running preflight check..."
python "$SKILL_DEST/scripts/setup.py" --check

echo ""
echo "Done! Open Claude Code and try:"
echo "  /watch https://youtu.be/dQw4w9WgXcQ what happens in this video?"
echo ""
echo "Optional: add a Whisper API key for videos without captions:"
echo "  mkdir -p ~/.config/watch"
echo "  echo 'GROQ_API_KEY=your-key' >> ~/.config/watch/.env"
