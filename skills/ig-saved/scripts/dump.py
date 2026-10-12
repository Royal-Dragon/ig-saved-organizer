"""Write the items Claude still has to extract into work/<category>.txt (captions + transcripts + frame hints).

Pending = in-scope items not yet in extracted/*.json, plus items extracted as `needs_content` (and not yet
`enriched`) that now have a transcript or a frame sheet. Re-run after each transcription pass.

Usage: dump.py
"""
import json
import re
from collections import defaultdict

from common import DATA, category_of, config, extracted_state, in_scope, load_json

CAPTION_CAP = 900
TRANSCRIPT_CAP = 1500


def clean(text):
    text = re.sub(r"[\[\({][^\]\)}]{120,}[\]\)}]", "", text)  # long keyword blocks
    lines = [l for l in text.splitlines() if not re.fullmatch(r"\s*[.•·]\s*", l)]
    while lines and (not lines[-1].strip() or lines[-1].count("#") >= 2):
        lines.pop()  # trailing hashtag walls
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()[:CAPTION_CAP]


def main():
    cfg = config()
    raw = json.loads((DATA / "raw.json").read_text())
    state = extracted_state()
    transcripts = load_json("transcripts.json", {})
    work = DATA / "work"
    work.mkdir(exist_ok=True)
    for f in work.glob("*.txt"):
        f.unlink()

    out = defaultdict(list)
    for i in raw:
        if not in_scope(i, cfg):
            continue
        pk = i["pk"]
        tr = transcripts.get(pk, {}).get("text", "")
        has_frames = (DATA / "frames" / f"{pk}.jpg").exists()
        prev = state.get(pk)
        if prev is None:
            retry = False
        elif prev.get("status") == "needs_content" and not prev.get("enriched") and (len(tr.split()) >= 10 or has_frames):
            retry = True
        else:
            continue
        block = [f"=== {pk} | @{i['author']} | {','.join(i['collections']) or '(no collection)'}"
                 + (" | RE-EXTRACT (replace the old entry)" if retry else ""), clean(i["caption"])]
        if tr:
            block.append(f"[transcript ({transcripts[pk]['lang']})] {tr[:TRANSCRIPT_CAP]}")
        if has_frames:
            block.append(f"[frames] {DATA / 'frames' / (pk + '.jpg')}")
        out[category_of(i, cfg) or "unsorted"].append("\n".join(block))

    for cat, blocks in out.items():
        (work / f"{cat}.txt").write_text("\n".join(blocks) + "\n")
        print(f"{cat:<14}{len(blocks):>5}  -> {work / (cat + '.txt')}")
    if not out:
        print("nothing pending")


if __name__ == "__main__":
    main()
