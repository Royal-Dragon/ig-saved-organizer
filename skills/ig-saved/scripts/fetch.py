"""Fetch your saved Instagram posts + collections -> $IG_SAVED_HOME/raw.json.

Usage: fetch.py [--limit N]     (N = max items per collection; 0 = all)
Needs IG_SESSIONID (your browser's instagram.com `sessionid` cookie) in $IG_SAVED_HOME/.env.
"""
import argparse
import json
import random
import time

from instagrapi import Client

from common import DATA, sessionid

ALL_SAVED = "ALL_MEDIA_AUTO_COLLECTION"


def to_item(m):
    return {
        "pk": str(m.pk),
        "url": f"https://www.instagram.com/{'reel' if m.product_type == 'clips' else 'p'}/{m.code}/",
        "is_reel": m.product_type == "clips",
        "author": m.user.username if m.user else None,
        "caption": m.caption_text or "",
        "taken_at": m.taken_at.isoformat() if m.taken_at else None,
        "collections": [],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    cl = Client()
    cl.delay_range = [1, 3]
    cl.login_by_sessionid(sessionid())

    items = {}
    for col in cl.collections():
        if col.type != "MEDIA":  # skip audio / product auto-collections
            continue
        print(f"collection: {col.name.strip()} ({col.media_count})", flush=True)
        for m in cl.collection_medias(col.id, amount=args.limit):
            items.setdefault(str(m.pk), to_item(m))["collections"].append(col.name.strip())
        time.sleep(random.uniform(2, 5))  # be gentle: avoid rate-limit flags

    # Saves in no named collection only appear in the "all saved" feed.
    print("all saved feed", flush=True)
    for m in cl.collection_medias(ALL_SAVED, amount=args.limit):
        items.setdefault(str(m.pk), to_item(m))

    DATA.mkdir(parents=True, exist_ok=True)
    out = DATA / "raw.json"
    out.write_text(json.dumps(list(items.values()), indent=2, ensure_ascii=False))
    print(f"wrote {len(items)} items -> {out}")


if __name__ == "__main__":
    main()
