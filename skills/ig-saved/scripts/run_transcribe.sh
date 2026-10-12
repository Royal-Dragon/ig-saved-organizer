#!/usr/bin/env bash
# Supervise transcribe.py: restart it after a crash, and kill -9 it if one reel is in flight
# longer than STUCK_SECS (catches deadlocks that no in-process timeout can interrupt).
# It resumes from its cache; the reel it was stuck on is recorded as failed via inflight.txt.
#
# Usage: run_transcribe.sh [transcribe.py args]      (run detached: setsid nohup ... &)
HERE="$(cd "$(dirname "$0")" && pwd)"
export IG_SAVED_HOME="${IG_SAVED_HOME:-$HOME/.ig-saved}"
PY="$IG_SAVED_HOME/.venv/bin/python"
STUCK_SECS=240

[[ -x "$PY" ]] || { echo "No venv at $IG_SAVED_HOME/.venv — run setup.sh first" >&2; exit 2; }

for attempt in $(seq 1 30); do
    "$PY" -u "$HERE/transcribe.py" "$@" &
    pid=$!
    while kill -0 "$pid" 2>/dev/null; do
        sleep 10
        marker="$IG_SAVED_HOME/inflight.txt"
        if [[ -f "$marker" ]] && (( $(date +%s) - $(stat -c %Y "$marker") > STUCK_SECS )); then
            echo "!! reel $(cat "$marker") stuck > ${STUCK_SECS}s — killing pid $pid" >&2
            kill -9 "$pid" 2>/dev/null
        fi
    done
    wait "$pid" && exit 0
    echo "!! transcribe.py exited abnormally (attempt $attempt) — restarting in 10s" >&2
    sleep 10
done
exit 1
