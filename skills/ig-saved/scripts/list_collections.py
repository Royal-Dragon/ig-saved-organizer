"""Show each collection with its size and sample captions, so Claude can propose a category mapping.

Usage: list_collections.py
"""
import json
import re
from collections import defaultdict

from common import DATA


def main():
    raw = json.loads((DATA / "raw.json").read_text())
    by = defaultdict(list)
    for i in raw:
        for c in i["collections"]:
            by[c].append(i)
    uncollected = [i for i in raw if not i["collections"]]
    print(f"{len(raw)} saved items, {len(raw) - len(uncollected)} in a collection, {len(uncollected)} in none\n")
    for name, xs in sorted(by.items(), key=lambda kv: -len(kv[1])):
        print(f"[{name}] {len(xs)} items")
        for i in xs[:4]:
            cap = re.sub(r"\s+", " ", re.sub(r"[#@]\S+", "", i["caption"])).strip()[:90]
            print(f"    - {cap or '(no caption)'}")


if __name__ == "__main__":
    main()
