"""Build one 4x3 contact sheet per reel (12 evenly spaced frames) -> $IG_SAVED_HOME/frames/<pk>.jpg.

For reels whose titles/ingredients are shown on screen (listicles). Claude reads the images directly.

Usage: frames.py PK [PK ...]
"""
import random
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from instagrapi import Client

from common import DATA, sessionid

OUT = DATA / "frames"


def contact_sheet(video, dest, n=12):  # listicles flash items for ~1s; 6 frames missed most of them
    dur = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
        capture_output=True, text=True, check=True,
    ).stdout)
    fps = n / (dur * 0.9)  # skip the first/last 5% (intros, end cards)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-ss", str(dur * 0.05), "-i", str(video),
         "-vf", f"fps={fps},scale=480:-2,tile=4x3", "-frames:v", "1", "-q:v", "3", str(dest)],
        check=True,
    )


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    todo = [pk for pk in sys.argv[1:] if not (OUT / f"{pk}.jpg").exists()]
    print(f"{len(todo)} to do", flush=True)

    cl = Client()
    cl.delay_range = [1, 3]
    cl.login_by_sessionid(sessionid())

    with tempfile.TemporaryDirectory() as tmp:
        for n, pk in enumerate(todo, 1):
            try:
                video = cl.video_download_by_url(cl.media_info(int(pk)).video_url, folder=Path(tmp))
                contact_sheet(video, OUT / f"{pk}.jpg")
                Path(video).unlink(missing_ok=True)
                print(f"[{n}/{len(todo)}] {pk}", flush=True)
            except Exception as e:
                print(f"  fail {pk}: {type(e).__name__}: {e}", flush=True)
            time.sleep(random.uniform(3, 6))


if __name__ == "__main__":
    main()
