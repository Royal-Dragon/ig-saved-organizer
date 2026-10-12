#!/usr/bin/env bash
# One-time setup: create $IG_SAVED_HOME (default ~/.ig-saved) with a Python venv and the dependencies.
# The venv lives in the data dir, not the plugin, so plugin updates never break it.
set -euo pipefail
export IG_SAVED_HOME="${IG_SAVED_HOME:-$HOME/.ig-saved}"
mkdir -p "$IG_SAVED_HOME"

command -v python3 >/dev/null || { echo "python3 is required" >&2; exit 1; }
python3 -c 'import sys; sys.exit(sys.version_info < (3, 10))' || { echo "Python 3.10+ is required" >&2; exit 1; }
command -v ffmpeg >/dev/null || echo "WARNING: ffmpeg not found — needed only for transcripts/frames (pacman -S ffmpeg | apt install ffmpeg | brew install ffmpeg)" >&2

if [[ ! -x "$IG_SAVED_HOME/.venv/bin/python" ]]; then
    python3 -m venv "$IG_SAVED_HOME/.venv"
fi
"$IG_SAVED_HOME/.venv/bin/pip" install -q --upgrade pip
# fetch/organize need only instagrapi; transcripts additionally need faster-whisper + numpy
"$IG_SAVED_HOME/.venv/bin/pip" install -q instagrapi faster-whisper numpy

if [[ ! -f "$IG_SAVED_HOME/.env" ]]; then
    printf '# Your instagram.com "sessionid" cookie (browser DevTools -> Application -> Cookies)\nIG_SESSIONID=\n' > "$IG_SAVED_HOME/.env"
fi
chmod 600 "$IG_SAVED_HOME/.env"
echo "ready: $IG_SAVED_HOME"
