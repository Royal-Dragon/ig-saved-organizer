"""End-to-end test of the offline stages (config -> dump -> check -> render) on synthetic data.

No Instagram access and no personal data: every reel below is made up.
Run: python -m unittest discover -s tests
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "skills" / "ig-saved" / "scripts"


def reel(pk, caption, collections, is_reel=True):
    return {"pk": pk, "url": f"https://www.instagram.com/{'reel' if is_reel else 'p'}/FAKE{pk}/", "is_reel": is_reel,
            "author": "someone", "caption": caption, "taken_at": None, "collections": collections}


LONG = " ".join(["word"] * 40)
RAW = [
    reel("1", "Pasta carbonara: eggs, guanciale, pecorino. " + LONG, ["Food"]),
    reel("2", "titles in video", ["Food"]),                      # thin caption -> needs transcript
    reel("3", LONG, ["Later", "Food"]),                          # two collections, different categories -> unsorted
    reel("4", LONG, ["Hidden"]),                                 # collection mapped to skip
    reel("5", LONG, []),                                         # no collection -> out of scope by default
    reel("6", "Build a CLI in Rust " + LONG, ["Later"]),
]
CONFIG = {"collections": {"food ": "recipe", "LATER": "watch_later", "hidden": "skip"}}  # also tests normalising


def run(script, home, *args):
    env = {**os.environ, "IG_SAVED_HOME": str(home)}
    return subprocess.run([sys.executable, str(SCRIPTS / script), *args], env=env, capture_output=True, text=True)


class PipelineTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name)
        self.out = self.home / "vault"
        (self.home / "raw.json").write_text(json.dumps(RAW))
        (self.home / "config.json").write_text(json.dumps({**CONFIG, "output_dir": str(self.out)}))
        (self.home / "extracted").mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def extract(self, name, entries):
        (self.home / "extracted" / f"{name}.json").write_text(json.dumps(entries))

    def test_dump_scopes_and_groups_items(self):
        r = run("dump.py", self.home)
        self.assertEqual(r.returncode, 0, r.stderr)
        work = {p.stem: p.read_text() for p in (self.home / "work").glob("*.txt")}
        self.assertEqual(set(work), {"recipe", "watch_later", "unsorted"})
        self.assertIn("=== 1 ", work["recipe"])
        self.assertIn("=== 2 ", work["recipe"])
        self.assertIn("=== 3 ", work["unsorted"])      # conflicting collections go to Claude
        self.assertIn("=== 6 ", work["watch_later"])
        everything = "".join(work.values())
        self.assertNotIn("=== 4 ", everything)           # skip
        self.assertNotIn("=== 5 ", everything)           # uncollected, include_uncollected is off

    def test_include_uncollected(self):
        cfg = json.loads((self.home / "config.json").read_text())
        (self.home / "config.json").write_text(json.dumps({**cfg, "include_uncollected": True}))
        run("dump.py", self.home)
        self.assertIn("=== 5 ", (self.home / "work" / "unsorted.txt").read_text())

    def test_needs_content_is_reextracted_once_a_transcript_exists(self):
        self.extract("recipe", [{"pk": "2", "name": "Mystery dish", "status": "needs_content"}])
        run("dump.py", self.home)
        self.assertNotIn("=== 2 ", (self.home / "work" / "recipe.txt").read_text())
        (self.home / "transcripts.json").write_text(json.dumps({"2": {"text": "add two cups of rice " * 3, "lang": "en"}}))
        run("dump.py", self.home)
        text = (self.home / "work" / "recipe.txt").read_text()
        self.assertIn("RE-EXTRACT", text)
        self.assertIn("[transcript (en)]", text)
        self.extract("recipe", [{"pk": "2", "name": "Mystery dish", "status": "needs_content", "enriched": True}])
        run("dump.py", self.home)
        self.assertNotIn("=== 2 ", (self.home / "work" / "recipe.txt").read_text() if (self.home / "work" / "recipe.txt").exists() else "")

    def test_check_flags_duplicates_and_unknown_pks(self):
        self.extract("recipe", [{"pk": "1", "name": "A", "status": "full"}])
        self.extract("watch_later", [{"pk": "1", "kind": "Movie", "title": "B", "status": "ok"},
                                     {"pk": "999", "kind": "Movie", "title": "C", "status": "ok"}])
        r = run("check.py", self.home)
        self.assertEqual(r.returncode, 1)
        self.assertIn("appears 2 times", r.stdout)
        self.assertIn("999 is not in raw.json", r.stdout)

    def test_render_writes_notes_and_assigns_unsorted(self):
        self.extract("recipe", [
            {"pk": "1", "name": "Carbonara", "cuisine": "Italian", "diet": "non-veg", "course": "Pasta", "status": "full"},
            {"pk": "2", "name": "Mystery dish", "cuisine": "?", "diet": "?", "course": "Pasta", "status": "name_only"}])
        self.extract("watch_later", [{"pk": "6", "kind": "Idea", "title": "Rust CLI", "note": "", "status": "needs_content"}])
        self.extract("unsorted", [{"pk": "3", "category": "watch_later", "kind": "Movie", "title": "Heat (1995)",
                                   "note": "", "status": "ok"}])
        self.assertEqual(run("check.py", self.home).returncode, 0)
        r = run("render.py", self.home)
        self.assertEqual(r.returncode, 0, r.stderr)
        lib = self.out / "IG Library"
        self.assertTrue((lib / "Recipes" / "Carbonara.md").exists())
        self.assertIn("guanciale", (lib / "Recipes" / "Carbonara.md").read_text())          # caption is copied verbatim
        self.assertIn("only in the video", (lib / "Recipes" / "Mystery dish.md").read_text())
        watch = (lib / "Watch Later.md").read_text()
        self.assertIn("Heat (1995)", watch)                                                  # unsorted entry landed here
        self.assertIn("Rust CLI ⚠︎", watch)
        self.assertIn("Needs Review", (lib / "Home.md").read_text())
        self.assertFalse((lib / "Health Guide.md").exists())                                 # empty sections write no page

    def test_render_removes_stale_pages(self):
        self.extract("wishlist", [{"pk": "1", "group": "Home", "item": "Lamp", "note": "", "status": "ok"}])
        run("render.py", self.home)
        self.assertTrue((self.out / "IG Library" / "Wishlist.md").exists())
        self.extract("wishlist", [])
        run("render.py", self.home)
        self.assertFalse((self.out / "IG Library" / "Wishlist.md").exists())

    def test_env_file_accepts_export_and_quotes(self):
        for line in ["IG_SESSIONID=abc123", "export IG_SESSIONID=abc123", '  export IG_SESSIONID="abc123"']:
            (self.home / ".env").write_text("# comment\n" + line + "\n")
            r = subprocess.run(
                [sys.executable, "-c", "import common; common.load_env(); import os; print(os.environ['IG_SESSIONID'])"],
                cwd=SCRIPTS, capture_output=True, text=True,
                env={k: v for k, v in {**os.environ, "IG_SAVED_HOME": str(self.home)}.items() if k != "IG_SESSIONID"})
            self.assertEqual(r.stdout.strip(), "abc123", f"{line!r}: {r.stderr}")

    def test_config_rejects_unknown_category(self):
        (self.home / "config.json").write_text(json.dumps({"collections": {"x": "nonsense"}}))
        r = run("dump.py", self.home)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Unknown categories", r.stderr + r.stdout)


if __name__ == "__main__":
    unittest.main()
