# edit.json

All times are **seconds as silence.py (or prep.py) printed them** — before your cut. Take numbers are the `[k]` it printed.

```json
{
  "keep": [0, 5, 6, 7, 8, 9, 10, 11, 12],
  "hooks_at_end": [],
  "captions": {
    "0": "هاد الفيديو ما منتجته | على CapCut | ولكن منتجته على Claude",
    "5": "أنا حالياً عم اشتغل | على Plugin جوّا Claude | منتجلي^2 هاد الفيديو"
  },
  "key": ["CapCut", "Claude", "Plugin", "200"],
  "caption_style": "default",
  "scenes": [ … see scenes.md … ],
  "punch": {"5": [1.0, 1.05], "6": [1.08, 1.08]},
  "kicks": [[27.58, 1.06], [41.22, 1.08]],
  "transitions": ["Pull Out", "Glare II"],
  "sfx": [["whoosh_up", 2.64], ["click", 32.7], ["pop", 7.46, 0.05]],
}
```

| field | meaning |
|---|---|
| `keep` | takes in output order. Retakes/duplicates simply left out. |
| `hooks_at_end` | takes (alternate hooks) appended after the last word; each starts clean (no caption crossing in) and gets the opening zoom. Give each its own written-hook scene with `"take": k`. |
| `captions` | per take: shown text, `|` = next caption. Must have the same number of words as whisper heard in that take: `word^2` = 1 shown word over 2 whisper words, `a~b` = 1 whisper word shown as 2. A take left out of `captions` uses whisper's words as they are (fix them!). |
| `key` | words drawn in the accent color, a bit bigger. 1–2 per caption at most. |
| `caption_style` | `default` (white + accent, slide up/pop) · `box` (dark rounded box, zoom out) · `big` (big 2–4 words, blur in) · `clean` (display font, fade in). Use a different one per Trial copy. |
| `punch` | take → [scale at start, scale at end]. Default alternates a slow push 1.0→1.05 and a static 1.08. The chin stays where it was. |
| `kicks` | [time, zoom factor] quick zoom on a strong word inside a long take (1.06–1.10; 1/1.08 to zoom back). |
| `transitions` | effects at take changes (≥5s apart, never around full-screen scenes): `Pull Out` (quick zoom punch), `Glare II` (soft white flash), `Shaky Inhale` (punch + small shake). Same names map to CapCut's transitions in the optional CapCut export. |
| `sfx` | [name, time, volume?]: `whoosh_up` `whoosh_down` `tap` `click` `pop` `shimmer` `counter` `glitch` `riser` `shutter` `sub` `thud`. Volume defaults to the config (0.05; the export normalizes the final loudness, so this is relative to the voice). |
| `extends` | another edit file to start from (Trial copies override only what changes). |
- A full working example (the plugin's own launch reel): `references/example-edit.json`.
