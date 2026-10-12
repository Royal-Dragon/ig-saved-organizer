"""Render extracted/*.json into Markdown notes under <output_dir>/IG Library/ (an Obsidian vault works great).

Re-runnable: it regenerates only files inside IG Library/ — edit the extracted JSON, not the notes.

Usage: render.py
"""
import json
import re
from collections import defaultdict
from pathlib import Path

from common import DATA, category_of, config, load_json

CFG = config()
OUT_DIR = Path(CFG.get("output_dir") or DATA / "out").expanduser()
LIB = OUT_DIR / "IG Library"
RAW = {i["pk"]: i for i in json.loads((DATA / "raw.json").read_text())}

WATCH_ORDER = ["Movie", "Series", "Anime", "Movie list", "Anime list", "Podcast / talk", "Game", "Food spot",
               "Shopping", "Place", "Event", "Tech resource", "Idea", "Product", "Info", "Story", "Reflection"]


def load(cat):
    """Entries for a category: extracted/<cat>.json plus unsorted.json entries assigned to it."""
    entries = []
    for name in (cat, "unsorted"):
        p = DATA / "extracted" / f"{name}.json"
        if p.exists():
            entries += [x for x in json.loads(p.read_text()) if name == cat or x.get("category") == cat]
    return [x for x in entries if x["pk"] in RAW]  # drop reels that no longer exist in the latest fetch


def reel(pk):
    return f"[reel]({RAW[pk]['url']})"


def cell(s):
    return str(s).replace("|", "\\|").replace("\n", " ")


def flag(x):
    return " ⚠︎" if x.get("status") == "needs_content" else ""


def table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(cell(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def page(name, title, body, intro=""):
    head = f"# {title}\n\n[[IG Library/Home|← Home]]\n\n" + (f"{intro}\n\n" if intro else "")
    (LIB / f"{name}.md").write_text(head + body.rstrip() + "\n")


def clean_caption(text):
    text = re.sub(r"[\[\({][^\]\)}]{120,}[\]\)}]", "", text)
    lines = [l for l in text.splitlines() if not re.fullmatch(r"\s*[.•·]\s*", l)]
    while lines and (not lines[-1].strip() or lines[-1].count("#") >= 2):
        lines.pop()
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def filename(s):
    return re.sub(r'[\\/:*?"<>|#^\[\]]', "", s).strip()


# ---------- sections: each returns the number of entries it rendered (0 = no page written) ----------

def watch_later():
    by = defaultdict(list)
    for x in load("watch_later"):
        by[x["kind"]].append(x)
    if not by:
        return 0
    parts = []
    for kind in sorted(by, key=lambda k: WATCH_ORDER.index(k) if k in WATCH_ORDER else 99):
        rows = [(x["title"] + flag(x), x.get("note", ""), reel(x["pk"])) for x in by[kind]]
        parts.append(f"## {kind} ({len(rows)})\n\n" + table(["Title", "Notes", "Link"], rows))
    page("Watch Later", "Watch Later", "\n\n".join(parts),
         "⚠︎ = details are only in the video; see [[IG Library/Needs Review|Needs Review]].")
    return sum(len(v) for v in by.values())


def reading_list():
    by, todo, other = defaultdict(list), [], []
    entries = load("reading")
    for x in entries:
        if x["status"] == "not_reading":
            other.append(x)
        elif not x.get("items") or x["status"] == "needs_content":
            todo.append(x)
        if x["status"] != "needs_content":
            for b in x.get("items", []):
                by[b["genre"]].append((b, x["pk"]))
    if not entries:
        return 0
    n = sum(len(v) for v in by.values())
    parts = [f"## {g} ({len(v)})\n\n" + table(["Title", "Author", "Type", "Link"],
             [(b["title"], b.get("author", ""), b.get("type", ""), reel(pk)) for b, pk in v]) for g, v in sorted(by.items())]
    if todo:
        parts.append(f"## Lists still to fill ({len(todo)})\n\nTitles are shown or spoken in the video.\n\n" +
                     "\n".join(f"- [ ] {x.get('hint', '')} — {reel(x['pk'])}" for x in todo))
    if other:
        parts.append(f"## Quotes & essays saved here ({len(other)})\n\n" +
                     "\n".join(f"- {x.get('hint', '')} — {reel(x['pk'])}" for x in other))
    page("Reading List", "Reading List", "\n\n".join(parts), f"{n} titles from your saved reels.")
    return n


def project_ideas():
    by = defaultdict(list)
    for x in load("project_idea"):
        by[x["kind"]].append(x)
    if not by:
        return 0
    parts = []
    for kind in ["Build idea", "Tool / library", "Learning resource"] + [k for k in by if k not in ("Build idea", "Tool / library", "Learning resource")]:
        items = []
        for x in by.get(kind, []):
            links = " · ".join(x.get("links", []))
            box = "- [ ] " if kind == "Build idea" else "- "
            items.append(f"{box}**{x['title']}**{flag(x)} — {x['pitch']}" + (f"\n  {links}" if links else "") + f" ({reel(x['pk'])})")
        if items:
            parts.append(f"## {kind} ({len(items)})\n\n" + "\n".join(items))
    page("Project Ideas", "Project Ideas", "\n\n".join(parts))
    return sum(len(v) for v in by.values())


def news():
    by = defaultdict(list)
    for x in load("news"):
        by[x["topic"]].append(x)
    if not by:
        return 0
    parts = [f"## {t} ({len(v)})\n\n" + "\n".join(f"- {x['summary']}{flag(x)} — {reel(x['pk'])}" for x in v)
             for t, v in by.items()]
    page("News", "News", "\n\n".join(parts), "One or two lines per reel.")
    return sum(len(v) for v in by.values())


def health():
    by = defaultdict(list)
    for x in load("health"):
        by[x["topic"]].append(x)
    if not by:
        return 0
    parts = []
    for t, v in by.items():
        blocks = []
        for x in v:
            tips = "\n".join(f"  - {tip}" for tip in x["tips"])
            blocks.append(f"- **{x['title']}**{flag(x)} — {reel(x['pk'])}\n{tips}")
        parts.append(f"## {t}\n\n" + "\n".join(blocks))
    page("Health Guide", "Health Guide", "\n\n".join(parts), "Grouped by goal.")
    return sum(len(v) for v in by.values())


def wishlist():
    by = defaultdict(list)
    for x in load("wishlist"):
        by[x["group"]].append(x)
    if not by:
        return 0
    parts = [f"## {g}\n\n" + "\n".join(
        f"- [ ] {x['item']}{flag(x)}" + (f" — {x['note']}" if x.get("note") else "") + f" ({reel(x['pk'])})" for x in v)
        for g, v in by.items()]
    page("Wishlist", "Wishlist", "\n\n".join(parts), "Things to buy or have.")
    return sum(len(v) for v in by.values())


def other():
    by = defaultdict(list)
    for x in load("other"):
        by[x.get("kind", "Other")].append(x)
    if not by:
        return 0
    parts = [f"## {k} ({len(v)})\n\n" + table(["Title", "Notes", "Link"],
             [(x["title"] + flag(x), x.get("note", ""), reel(x["pk"])) for x in v]) for k, v in by.items()]
    page("Other", "Other", "\n\n".join(parts))
    return sum(len(v) for v in by.values())


def recipes():
    entries = [x for x in load("recipe") if x["status"] != "not_recipe"]
    if not entries:
        return 0
    (LIB / "Recipes").mkdir(parents=True, exist_ok=True)
    rows = []
    for x in entries:
        fn = filename(x["name"])
        raw = RAW[x["pk"]]
        body = (clean_caption(raw["caption"]) if x["status"] != "name_only"
                else "_The recipe is only in the video — watch the reel._")
        if transcript := (load_json("transcripts.json", {}).get(x["pk"], {}).get("text") if x["status"] != "full" else None):
            body += f"\n\n## Transcript (auto-generated, may contain errors)\n\n{transcript}"
        front = "\n".join(["---", f"cuisine: {x.get('cuisine', '')}", f"diet: {x.get('diet', '')}",
                           f"course: {x.get('course', '')}", f"completeness: {x['status']}", f"source: {raw['url']}",
                           f"creator: \"@{raw['author']}\"", "tags: [recipe]", "---"])
        (LIB / "Recipes" / f"{fn}.md").write_text(
            f"{front}\n# {x['name']}\n\n[[IG Library/Recipes|← All recipes]] · [Watch the reel]({raw['url']})\n\n"
            f"## Recipe (from the caption)\n\n{body}\n")
        rows.append((x.get("course", "Other"), f"[[IG Library/Recipes/{fn}\\|{x['name']}]]", x.get("cuisine", ""),
                     x.get("diet", ""), x["status"].replace("_", " ")))
    by = defaultdict(list)
    for r in sorted(rows):
        by[r[0]].append(r[1:])
    parts = [f"## {c} ({len(v)})\n\n" + table(["Recipe", "Cuisine", "Diet", "In caption"], v) for c, v in by.items()]
    page("Recipes", "Recipes", "\n\n".join(parts),
         "*In caption*: full = method included, ingredients only, or name only (watch the reel).")
    return len(entries)


def needs_review():
    by = defaultdict(list)
    labels = {"watch_later": "Watch Later", "reading": "Reading List", "project_idea": "Project Ideas", "news": "News",
              "health": "Health Guide", "wishlist": "Wishlist", "other": "Other"}
    for cat, label in labels.items():
        for x in load(cat):
            if x.get("status") == "needs_content":
                what = x.get("title") or x.get("hint") or x.get("summary") or x.get("item") or x.get("name") or ""
                by[label].append(f"- [ ] {what} — {reel(x['pk'])}")
    n = sum(len(v) for v in by.values())
    if not n:
        return 0
    parts = [f"## {k} ({len(v)})\n\n" + "\n".join(v) for k, v in by.items()]
    page("Needs Review", "Needs Review", "\n\n".join(parts),
         f"{n} reels where the caption is only a hook (\"comment X for the link\", \"titles in video\"). "
         "Open the reel, or run the transcription step to fill these in.")
    return n


def failed_reels():
    failed = load_json("transcripts_failed.json", {})
    failed = {pk: e for pk, e in failed.items() if pk in RAW}
    if not failed:
        return 0

    def why(err):
        if "Timeout" in err:
            return "timed out"
        if "JSONDecode" in err or "GraphqlError" in err:
            return "Instagram error (post may be deleted or private)"
        if "ffmpeg" in err:
            return "video file unreadable"
        return "crashed or hung the process"

    by = defaultdict(list)
    for pk, err in failed.items():
        i = RAW[pk]
        cat = (category_of(i, CFG) or "unsorted").replace("_", " ").title()
        snippet = re.sub(r"\s+", " ", re.sub(r"[#@]\S+", "", i["caption"])).strip()[:70]
        by[cat].append(f"- [ ] {reel(pk)} — @{i['author']}: {snippet or '(no caption)'} — *{why(err)}*")
    parts = [f"## {k} ({len(v)})\n\n" + "\n".join(v) for k, v in by.items()]
    page("Failed Reels", "Failed Reels", "\n\n".join(parts),
         f"{len(failed)} reels whose audio couldn't be transcribed. *Timed out* and *crashed* ones may work on a retry; "
         "*Instagram error* usually means the post is gone.")
    return len(failed)


def main():
    LIB.mkdir(parents=True, exist_ok=True)
    for old in [*LIB.glob("*.md"), *(LIB / "Recipes").glob("*.md")]:
        old.unlink()  # generated files only; avoids stale pages when a section becomes empty
    counts = {
        "Watch Later": watch_later(), "Reading List": reading_list(), "Recipes": recipes(),
        "Project Ideas": project_ideas(), "News": news(), "Health Guide": health(), "Wishlist": wishlist(),
        "Other": other(), "Needs Review": needs_review(), "Failed Reels": failed_reels(),
    }
    units = {"Reading List": "titles", "Recipes": "recipes", "Needs Review": "reels", "Failed Reels": "reels"}
    rows = "\n".join(f"- [[IG Library/{k}|{k}]] — {v} {units.get(k, 'items')}" for k, v in counts.items() if v)
    (LIB / "Home.md").write_text("# IG Library\n\nYour saved Instagram reels, organised.\n\n" + rows + "\n")
    for k, v in counts.items():
        print(f"{k:<14}{v:>5}")
    print(f"-> {LIB}")


if __name__ == "__main__":
    main()
