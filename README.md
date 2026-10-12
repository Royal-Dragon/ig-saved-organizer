# ig-saved-organizer

A [Claude Code](https://claude.com/claude-code) plugin that turns your **saved Instagram reels** into organized
Markdown notes — a watch-later table, a reading list, recipe notes, project ideas, a news digest, a health guide and a
wishlist — built from your own collections. Works great as an [Obsidian](https://obsidian.md) vault.

Everything runs on your machine. Nothing is uploaded anywhere except what Claude itself reads in your session.

## Install

```bash
claude plugin marketplace add Royal-Dragon/ig-saved-organizer && claude plugin install ig-saved@ig-saved-organizer
```

Then, in Claude Code, run:

```
/ig-saved
```

Claude walks you through the rest. Requirements: Python 3.10+, and `ffmpeg` only if you want transcripts.

## What happens when you run it

1. **Setup** – creates `~/.ig-saved/` with a Python venv (your data never goes in the plugin folder).
2. **Login** – you paste your instagram.com `sessionid` cookie into `~/.ig-saved/.env` yourself (never into chat).
3. **Fetch** – pulls every save and which collection it's in.
4. **Map** – Claude shows your collections and proposes a category for each (`watch_later`, `reading`, `recipe`,
   `project_idea`, `news`, `health`, `wishlist`, `other`, `skip`); you confirm and pick the output folder.
5. **Extract** – Claude reads each caption and writes structured entries (titles, authors, ingredients, summaries).
6. **Render** – writes `IG Library/` into your folder: one note per category, one note per recipe, plus a
   *Needs Review* list.
7. **Optional: fill the gaps** – many reels only say "comment GUIDE for the link"; the real content is in the video.
   Claude can transcribe those with [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (CPU, ~1 min per reel)
   and read on-screen text from frame contact sheets, then update the notes.

## Please read: risks and limits

- **It uses Instagram's unofficial private API** ([instagrapi](https://github.com/subzeroid/instagrapi)) with your
  login. That's against Instagram's terms and can trigger rate limits, a login challenge, or an account restriction.
  Use a secondary account if you can, run it once at a gentle pace, and don't loop it.
- **Your `sessionid` is a full login credential.** Keep `~/.ig-saved/.env` private (the setup script sets `chmod 600`).
  Cookies expire; if fetching starts failing with `login_required`, log in again and re-copy it.
- **Captions are often just hooks.** Expect a real share of reels to land in *Needs Review* until you run the
  transcription step. Small Whisper models are weak on some languages (e.g. Telugu came out as gibberish), so those
  stay flagged instead of being guessed at.
- **Claude's extraction is a draft.** It's told to use only what's in the caption/transcript/frames, but check
  anything that matters (quantities, medical advice).
- Instagram's collection counts run slightly higher than what the API returns (deleted or private posts).
- Transcription downloads each video through your login. Keep the machine awake; if it sleeps, rerun and it resumes.

## Where things live

| Path | What |
|---|---|
| `~/.ig-saved/` (or `$IG_SAVED_HOME`) | cookie, `raw.json`, `config.json`, transcripts, extracted JSON, venv |
| `<your output folder>/IG Library/` | the generated notes — regenerated each run, so don't hand-edit inside it |

To remove all your data: `rm -rf ~/.ig-saved`.

## How it works

`fetch.py` → `list_collections.py` → *(you confirm a mapping)* → `dump.py` → *(Claude writes `extracted/*.json`)* →
`check.py` → `render.py`, with `run_transcribe.sh` / `frames.py` for reels whose content is only in the video.

- `run_transcribe.sh` supervises the transcriber: it restarts it after a crash and `kill -9`s a reel that hangs for
  4 minutes (an in-process timeout can't interrupt a thread stuck in C code). The reel is recorded in
  `transcripts_failed.json` and skipped next time.
- `dump.py` is incremental: it only lists items not yet extracted, plus `needs_content` ones that now have a
  transcript or frames.
- Extraction schemas are in [`skills/ig-saved/references/schemas.md`](skills/ig-saved/references/schemas.md).

## Development

```bash
python -m unittest discover -s tests     # offline pipeline tests on synthetic data
claude plugin validate .                 # manifest check
```

The tests cover config mapping, scoping, incremental re-extraction, validation and rendering. Fetching and
transcription talk to Instagram and aren't covered by them.

## License

MIT — see [LICENSE](LICENSE). Not affiliated with Instagram, Meta, or Anthropic.
