"""Validate extracted/*.json and report coverage. Exit code 1 if anything is wrong.

Checks: valid JSON, every entry has a pk that exists in raw.json, no pk appears twice, `unsorted.json` entries
carry a valid `category`, statuses are known. Then prints how many in-scope items are still not extracted.

Usage: check.py
"""
import json
import sys
from collections import Counter

from common import CATEGORIES, DATA, config, in_scope

STATUSES = {"ok", "needs_content", "not_reading", "not_recipe", "full", "ingredients_only", "name_only"}


def main():
    raw = {i["pk"]: i for i in json.loads((DATA / "raw.json").read_text())}
    cfg = config()
    seen, problems, statuses = Counter(), [], Counter()
    for f in sorted((DATA / "extracted").glob("*.json")):
        try:
            entries = json.loads(f.read_text())
        except json.JSONDecodeError as e:
            problems.append(f"{f.name}: invalid JSON ({e})")
            continue
        for x in entries:
            pk = x.get("pk")
            if pk not in raw:
                problems.append(f"{f.name}: pk {pk} is not in raw.json")
            seen[pk] += 1
            statuses[x.get("status")] += 1
            if x.get("status") not in STATUSES:
                problems.append(f"{f.name}: pk {pk} has unknown status {x.get('status')!r}")
            if f.stem == "unsorted" and x.get("category") not in CATEGORIES:
                problems.append(f"unsorted.json: pk {pk} needs a valid `category`, got {x.get('category')!r}")
    problems += [f"pk {pk} appears {n} times across extracted/*.json" for pk, n in seen.items() if n > 1]

    todo = [pk for pk, i in raw.items() if in_scope(i, cfg) and pk not in seen]
    print(f"extracted {sum(seen.values())} entries | statuses {dict(statuses)} | in scope but not extracted: {len(todo)}")
    for p in problems:
        print("PROBLEM:", p)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
