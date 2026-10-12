---
name: ig-saved
description: Fetch the user's saved Instagram reels and organize them into Markdown notes (watch-later tables, reading list, recipes, project ideas, news digest, health guide, wishlist), using their collections plus Claude's reading of captions and optional Whisper transcripts. Use when the user runs /ig-saved or asks to organize, sort, export, or make notes from their Instagram saved reels, saved posts or collections.
---

# ig-saved — turn saved Instagram reels into organized notes

Everything runs locally. State lives in `DATA = ${IG_SAVED_HOME:-~/.ig-saved}`, never in the plugin.
`SCRIPTS` = the `scripts/` folder next to this file (use the "Base directory for this skill" shown above).
`PY` = `$DATA/.venv/bin/python`.

## Ground rules

- **Never ask the user to paste their `sessionid` cookie into chat.** It is a full login credential. They put it in
  `$DATA/.env` themselves.
- This uses Instagram's unofficial private API through the user's own login. Say once, plainly: it can trigger
  rate limits or an account flag, a secondary account is safer, and it should be a single slow run, not a loop.
- Facts come only from the caption, transcript, or frame image. Never invent a title, ingredient, or quantity. If the
  content isn't there, say so with `status: needs_content`.
- Don't re-fetch or re-transcribe what's already cached. Every stage resumes from files in `$DATA`.

## Steps

**1. Setup (once).** Run `bash $SCRIPTS/setup.sh`. Then tell the user to open `$DATA/.env` in their editor and paste their
instagram.com `sessionid` cookie after `IG_SESSIONID=` (browser DevTools → Application → Cookies → instagram.com).
Wait for them to confirm. ffmpeg is needed only for step 6.

**2. Fetch.** Test first: `$PY $SCRIPTS/fetch.py --limit 5`. If it logs in and lists collections, run the full
`$PY $SCRIPTS/fetch.py`. It writes `$DATA/raw.json`. Instagram's collection counts can be a little higher than what
the API returns (deleted/private posts) — that's normal.

**3. Map collections to categories.** Run `$PY $SCRIPTS/list_collections.py`. Propose a mapping from each of the user's
collection names (use the sample captions when a name is ambiguous) to one of:
`watch_later` · `reading` · `recipe` · `project_idea` · `news` · `health` · `wishlist` · `other` · `skip`.
Confirm with AskUserQuestion, also asking (a) the output folder (an Obsidian vault is ideal; default
`$DATA/out`) and (b) whether to include saves that are in no collection (default no — they're often the majority and
have no folder hint, so start with the collections). Write `$DATA/config.json`:

```json
{"collections": {"my food folder": "recipe", "watch later": "watch_later"},
 "output_dir": "~/MyVault", "include_uncollected": false}
```

**4. Extract.** Run `$PY $SCRIPTS/dump.py`. It writes `$DATA/work/<category>.txt` (one per category; `unsorted.txt` holds
items whose collections conflict or that have none). Read each file and write `$DATA/extracted/<category>.json`
following `references/schemas.md` — one entry per reel, every `pk` exactly once. For `unsorted`, add a `category`
field to each entry. Large files: read them in chunks. Copy recipes' text via the renderer (it prints the caption
verbatim) — don't retype quantities. Then run `$PY $SCRIPTS/check.py` and fix every PROBLEM it prints.

**5. Render.** `$PY $SCRIPTS/render.py` writes `IG Library/` under the output folder (Home, one note per category,
a note per recipe, Needs Review). Report the counts, and how many reels are `needs_content`.

**6. Fill the gaps (optional — ask first).** Reels marked `needs_content` have captions that are only a hook
("comment GUIDE for the link", "titles in video"). Offer transcripts, and state the cost honestly: Whisper runs on CPU
at roughly 1 minute per reel, the machine must stay awake, and it downloads each video through the user's
login (same account-risk note as above). If they agree, run it detached so it survives the session:

```bash
setsid nohup bash $SCRIPTS/run_transcribe.sh >> $DATA/transcribe.log 2>&1 < /dev/null &
```

`run_transcribe.sh` restarts after a crash and kills a reel that hangs for 4 minutes; failures are recorded in
`$DATA/transcripts_failed.json` and skipped (use `--retry-failed` to try them again). Check progress with
`tail $DATA/transcribe.log`. When it ends, run `dump.py` again — it now lists only the re-extractable items, with
transcripts attached — extract them, and replace the old entries (same `pk`; never leave duplicates). If a reel is a
listicle whose titles are shown on screen (empty or tiny transcript), run `$PY $SCRIPTS/frames.py <pk> ...`, then
view each `$DATA/frames/<pk>.jpg` and read the items off the contact sheet. If something still can't be found, keep
`status: needs_content` and add `"enriched": true` so it isn't offered again. Finish with `check.py` and `render.py`.

**7. Later runs.** New saves: re-run `fetch.py`, then `dump.py` (it only lists what isn't extracted yet), extract,
`check.py`, `render.py`.

## Notes

- Non-English transcripts from the small Whisper model can be gibberish (Telugu was). If a transcript doesn't read like
  real language, don't extract from it.
- `render.py` regenerates `IG Library/` completely. Tell the user not to hand-edit inside it.
- If the user asks to remove their data: delete `$DATA` (it holds the cookie, raw saves, and transcripts).
