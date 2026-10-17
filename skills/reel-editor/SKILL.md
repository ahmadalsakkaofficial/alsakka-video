---
name: reel-editor
description: يمنتج فيديو كلام للكاميرا (ريل 9:16) من الملف الخام لـ MP4 جاهز للنشر — بيقص ويشيل السكتات والإعادات، بيحط هوك مكتوب وكابشن عربي بتوقيت الكلمة، موشن غرافيك من مكتبة المشاهد، زوم وترانزيشن وساوند إفكت. بدون أي برنامج مونتاج. Use when the user says "منتجلي هالفيديو"، "منتج الفيديو"، "شيل السكتات"، "حط كابشن"، "سويلي موشن"، "edit this reel", or gives a video file to edit. Also for Trial Reel copies with other hooks ("سويلي نسخ بالهوكات التانية"), and — only if they ask — to also put the edit in CapCut.
---

# Raw video → finished reel (MP4)

You are the editor. The user gives a video file (or several takes); you hand back **one MP4 ready to post**. No editing app is needed.
Scripts: `S="${CLAUDE_PLUGIN_ROOT}/scripts"`. Work folder: `W=~/Movies/alsakka-video/<short-name>` (one per video). Talk to the user in their dialect, short and clear.

## 0 · Before anything
- First time on this Mac (no `~/.alsakka-video/bin/face`, or a script says "not found") → run the **setup** skill.
- Ask only what's missing: the video file path(s) (they can drag the file into the chat). If they pasted a script, keep it: it helps the transcription and the caption spelling.

## 1 · Listen to the video
```bash
python3 "$S/prep.py" "$W" "<video.mov>" ["<take2.mov>" …] --prompt "<English terms / names they say>"
python3 "$S/silence.py" "$W"          # removes the pauses, splits at sentence ends → prints numbered takes
```
`prep.py` transcribes word by word (whisper medium — slow on CPU, ~5–10× the video length: run it in the background and tell the user), re-transcribes any stretch whisper skipped, and measures the chin. `silence.py` prints `[k] start–end  text` per take: these numbers and times are what edit.json uses.
If the video is already cut by the user, skip `silence.py`.

## 2 · Decide the cut
Read the takes. Drop retakes, false starts and duplicates (keep the better one). If they filmed **several hooks**: open with the ONE best hook + the script, and put the other hooks in `hooks_at_end` (appended after the last word as Trial Reel material, each with its own written hook).

## 3 · Plan the edit → `$W/edit.json`
Fields: `references/edit-json.md`. Scenes: `references/scenes.md`. What matters most:
- **Written hook on screen from frame 1** (a `hook` / `hookx` / `clock` scene with `"take": <first take>`), in the speaker's own words.
- **Something changes every ≤ 4 s**: a scene, a cut, a punch-in or a `kicks` zoom. `build.py` warns about gaps.
- **Be creative from the meaning, not a template**: a product they name → its real logo (from `/Applications`, see scenes.md); a verb → a literal object doing it (scissors that cut, a clock that turns); talking about the video itself → a meta move (`pull`: the video inside its own timeline). Plain text cards are the fallback, not the plan.
- Scenes sit **above the head** or full screen — never over the face, never a split screen. High head in the frame (prep prints "face top" < ~650px) → `sc` 0.75–0.85.
- Captions: phrases of 2–5 words, never ending on a small word (ما، من، على، عم، اللي…), never splitting a phrase. Write words the way they really talk; fix whisper's spelling. **No period at the end.** 1–2 key words per caption in `key`.
- SFX subtle, only on meaningful beats (a scene entering, a snip, a check). No end card, no progress bar: the video ends on the last word.

## 4 · Preview → render → export
```bash
python3 "$S/build.py" "$W"                                   # plan + checks (4-second rule)
node "$S/render.js" "$W" edit --stills && python3 "$S/preview.py" "$W" edit
#   → LOOK at $W/preview_edit.jpg: text overflowing a card, a card touching the head, broken Arabic, a scene before its word → fix edit.json, rebuild
node "$S/render.js" "$W" edit                                # each scene → transparent .mov (cached by content)
node "$S/render.js" "$W" edit --captions                     # captions track
python3 "$S/export.py" "$W" edit                             # → $W/edit.mp4  (1080×1920, 30fps, loudness normalized)
```

## 5 · Check, then deliver
Run the `reel-qa` agent on `$W` + `edit`. Fix every 🔴 and export again. Then send the user the MP4 (and its path), with 3–4 lines: length, what's in it, words whisper was unsure about, anything to check by ear.

## Trial Reel copies (other hooks)
For each alternate hook: `$W/edit_t1.json` = `{"extends": "edit.json", "keep": [<that hook take>, …], "hooks_at_end": [], "caption_style": "box", "transitions": ["Pull Out"]}` + its own hook scene. Each copy must differ beyond the hook: its own cut/length, caption style (`box` / `big` / `clean`), transitions. Then `build.py "$W" edit_t1.json` → `render.js "$W" edit_t1` (+ `--captions`) → `export.py "$W" edit_t1` → `$W/edit_t1.mp4`.

## Optional: also in CapCut (only if they ask to tweak by hand)
They create a project + timeline in CapCut desktop (empty is fine) and close CapCut. Then `python3 "$S/capcut_write.py" "$W" edit "<project>" "<timeline>"` writes every track (takes with zoom keyframes, scenes, captions, transitions, SFX) and backs up their timeline first. `python3 "$S/capcut.py" list` shows project/timeline names.

## When something breaks
- `take k: N caption tokens vs M whisper words` → that take's caption text has a different word count than whisper heard: `word^2` = one shown word over two whisper words, `a~b` = one whisper word shown as two.
- Chrome / whisper / ffmpeg not found → setup skill.
- Export looks shifted or a scene is missing → `build.py` again (it re-plans), then render (only changed scenes re-render), then export.
