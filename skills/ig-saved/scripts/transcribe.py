"""Transcribe reels whose caption doesn't carry the content -> $IG_SAVED_HOME/transcripts.json (resumable).

Targets: in-scope reels with a thin caption, plus reels already extracted as `needs_content`.
Run it through run_transcribe.sh, which restarts it after a crash and kills it if a reel hangs.

Usage: transcribe.py [--limit N] [--model small] [--retry-failed]
"""
import argparse
import json
import os
import random
import subprocess
import tempfile
import time
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel
from instagrapi import Client

from common import DATA, THIN_WORDS, config, extracted_state, in_scope, sessionid, words

OUT = DATA / "transcripts.json"
FAILED = DATA / "transcripts_failed.json"  # pk -> last error; skipped unless --retry-failed
INFLIGHT = DATA / "inflight.txt"  # pk being processed; run_transcribe.sh kills us if it gets stale


def decode(path):
    # faster-whisper's own decoder breaks on newer PyAV, so feed it ffmpeg's 16 kHz mono float32 samples
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
        capture_output=True, check=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.float32)


def targets(items, cfg, state):
    for i in items:
        if not (in_scope(i, cfg) and i["is_reel"]):
            continue
        needs = state.get(i["pk"], {}).get("status") == "needs_content"
        if words(i["caption"]) < THIN_WORDS or needs:
            yield i


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--model", default="small")
    ap.add_argument("--retry-failed", action="store_true")
    args = ap.parse_args()

    done = json.loads(OUT.read_text()) if OUT.exists() else {}
    failed = json.loads(FAILED.read_text()) if FAILED.exists() else {}
    if INFLIGHT.exists():  # previous run died mid-reel: blame that reel so a crash can't loop
        pk = INFLIGHT.read_text().strip()  # empty after an unclean shutdown (zero-length file)
        if pk:
            failed[pk] = "crashed or hung the process"
            FAILED.write_text(json.dumps(failed, indent=1))
        INFLIGHT.unlink()

    skip = done.keys() | (set() if args.retry_failed else failed.keys())
    raw = json.loads((DATA / "raw.json").read_text())
    todo = [i for i in targets(raw, config(), extracted_state()) if i["pk"] not in skip]
    if args.limit:
        todo = todo[: args.limit]
    print(f"{len(done)} cached, {len(failed)} failed, {len(todo)} to do", flush=True)

    cl = Client()
    cl.delay_range = [1, 3]
    cl.login_by_sessionid(sessionid())
    model = WhisperModel(args.model, device="cpu", compute_type="int8", cpu_threads=os.cpu_count() or 4)

    with tempfile.TemporaryDirectory() as tmp:
        for n, item in enumerate(todo, 1):
            INFLIGHT.write_text(item["pk"])
            try:
                url = cl.media_info(int(item["pk"])).video_url
                path = cl.video_download_by_url(url, folder=Path(tmp))
                segs, info = model.transcribe(decode(path), vad_filter=True)
                text = " ".join(s.text.strip() for s in segs)
                done[item["pk"]] = {"text": text, "lang": info.language}
                Path(path).unlink(missing_ok=True)
            except Exception as e:  # keep going; the reel is recorded as failed
                print(f"  fail {item['pk']}: {type(e).__name__}: {e}", flush=True)
                failed[item["pk"]] = f"{type(e).__name__}: {e}"[:300]
                FAILED.write_text(json.dumps(failed, indent=1))
                continue
            finally:
                INFLIGHT.unlink(missing_ok=True)
            failed.pop(item["pk"], None)
            FAILED.write_text(json.dumps(failed, indent=1))
            OUT.write_text(json.dumps(done, ensure_ascii=False, indent=1))
            print(f"[{n}/{len(todo)}] {info.language} {len(text.split())}w {item['url']}", flush=True)
            time.sleep(random.uniform(3, 6))


if __name__ == "__main__":
    main()
