"""Shared helpers. All state lives in $IG_SAVED_HOME (default ~/.ig-saved), never in the plugin."""
import json
import os
import re
from pathlib import Path

DATA = Path(os.environ.get("IG_SAVED_HOME", Path.home() / ".ig-saved")).expanduser()
CATEGORIES = ["watch_later", "reading", "recipe", "project_idea", "news", "health", "wishlist", "other", "skip"]
THIN_WORDS = 25  # captions shorter than this (excluding #tags/@mentions/urls) rarely contain the content


def load_env():
    """Read $IG_SAVED_HOME/.env (KEY=value or `export KEY=value` lines) into os.environ, keeping real env vars."""
    f = DATA / ".env"
    if f.exists():
        for line in f.read_text().splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.removeprefix("export ").split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("'\""))


def sessionid():
    load_env()
    if not os.environ.get("IG_SESSIONID"):
        raise SystemExit(f"IG_SESSIONID not set. Put IG_SESSIONID=<cookie> in {DATA / '.env'} (chmod 600).")
    return os.environ["IG_SESSIONID"]


def load_json(name, default=None):
    p = DATA / name
    return json.loads(p.read_text()) if p.exists() else default


def config():
    p = DATA / "config.json"
    if not p.exists():
        raise SystemExit(f"{p} not found. Map your collections to categories first (SKILL.md step 3).")
    cfg = json.loads(p.read_text())
    cfg["collections"] = {k.strip().lower(): v for k, v in cfg.get("collections", {}).items()}
    bad = {v for v in cfg["collections"].values()} - set(CATEGORIES)
    if bad:
        raise SystemExit(f"Unknown categories in config.json: {sorted(bad)}. Allowed: {CATEGORIES}")
    return cfg


def category_of(item, cfg):
    """Category for an item from its collection names, or None if unmapped/conflicting (Claude decides)."""
    cats = {cfg["collections"][c.strip().lower()] for c in item["collections"] if c.strip().lower() in cfg["collections"]}
    return cats.pop() if len(cats) == 1 else None


def in_scope(item, cfg):
    """Items to process: in at least one collection (or all items if include_uncollected), and not skipped."""
    if not item["collections"] and not cfg.get("include_uncollected", False):
        return False
    return category_of(item, cfg) != "skip"


def words(caption):
    return len(re.sub(r"[#@]\S+|https?://\S+", "", caption).split())


def extracted_state():
    """pk -> extracted entry, across every extracted/*.json (each pk should appear once)."""
    state = {}
    for f in sorted((DATA / "extracted").glob("*.json")):
        for x in json.loads(f.read_text()):
            state[x["pk"]] = x
    return state
