# Extraction schemas

Write one JSON array per category to `$DATA/extracted/<category>.json`. Every entry has a `pk` (the number after
`===` in the work file) and a `status`. Each `pk` appears exactly once across all files; `check.py` enforces it.

**`status`**: `ok` (the content is in the caption/transcript/frames) · `needs_content` (it's only in the video and
you couldn't recover it) · category extras below. Add `"enriched": true` to a `needs_content` entry once you've
already tried the transcript/frames, so it isn't offered again.

`unsorted.json`: same shapes as below, with an added `"category": "<one of the categories>"` on each entry.

## watch_later.json
```json
{"pk": "1", "kind": "Movie", "title": "Heat (1995)", "note": "Michael Mann crime drama", "status": "ok"}
```
`kind` is free text; these sort first, in this order: Movie, Series, Anime, Movie list, Anime list, Podcast / talk,
Game, Food spot, Shopping, Place, Event, Tech resource, Idea, Product, Info, Story, Reflection. For list-reels, put the
titles in `note`, separated by " · ".

## reading.json
```json
{"pk": "2", "items": [{"title": "Piranesi", "author": "Susanna Clarke", "type": "book", "genre": "Fiction"}], "status": "ok"}
{"pk": "3", "items": [], "status": "needs_content", "hint": "6 books on AI, titles shown on screen"}
{"pk": "4", "items": [], "status": "not_reading", "hint": "a quote reel"}
```
One reel can yield many `items`. `type`: book, essay, website, paper, …. Use `not_reading` for saves in a
books-like collection that aren't reading material.

## recipe.json
```json
{"pk": "5", "name": "Chicken Shorba", "cuisine": "North Indian", "diet": "non-veg", "course": "Soup", "status": "full"}
```
`status`: `full` (method in the caption) · `ingredients_only` · `name_only` (recipe is in the video) · `not_recipe`
(something else in the folder, e.g. a product) · `needs_content`. The renderer copies the caption into the note
verbatim — do not transcribe quantities yourself. If a transcript exists for a non-`full` recipe it is appended.

## project_idea.json
```json
{"pk": "6", "kind": "Build idea", "title": "Phone-controlled p5.js game", "pitch": "One or two sentences.",
 "links": ["https://github.com/example/repo"], "status": "ok"}
```
`kind`: `Build idea` (gets a checkbox) · `Tool / library` · `Learning resource` · or your own.

## news.json
```json
{"pk": "7", "topic": "AI tools", "summary": "One or two lines: what the reel actually says.", "status": "ok"}
```

## health.json
```json
{"pk": "8", "topic": "Mobility", "title": "5-minute morning flow", "tips": ["Cat-cow", "Thread the needle"], "status": "ok"}
```
Merge reels about the same body area under one `topic`.

## wishlist.json
```json
{"pk": "9", "group": "Room decor", "item": "Floor lamp", "note": "warm light", "status": "ok"}
```

## other.json
```json
{"pk": "10", "kind": "Reflection", "title": "…", "note": "…", "status": "ok"}
```
