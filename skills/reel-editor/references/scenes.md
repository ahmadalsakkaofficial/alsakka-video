# Scene library

Every scene is a transparent 1080×1920 overlay rendered from `assets/scenes/<pack>.html` and placed on the «موشن» track.
In `edit.json` a scene is one object in `scenes`:

```json
{"name": "hook", "pack": "tech", "kind": "hook", "take": 0, "to": 3.85,
 "a": "هاد الفيديو ما منتجته على", "fromImg": "logos/capcut.png", "fromName": "CapCut",
 "toImg": "logos/claude.png", "toName": "Claude", "b": "ولكن منتجته على *Claude*",
 "marks": {"strike": 1.62, "flip": 2.64, "b": 2.64}}
```

- `at` / `to`: timeline seconds (as printed by prep.py). Use `"take": k` instead of `at` to start exactly on take k's first frame (always do this for the opening hook).
- `marks`: moments inside the scene, given as **timeline seconds of the spoken word** (build.py converts them). `durs`: plain durations in seconds (e.g. typing speed).
- `*word*` in any text = accent color. Text must be the speaker's own words (verbatim or a shortened subset). No periods at the end.
- `full: true` = full-screen scene (covers the speaker; captions drop to y≈1420). Everything else sits **above the head** in a card at y≈100–480.
- `sc` (0.7–1): shrink an above-head card when the speaker's head is high in the frame (prep.py prints "face top": if it's under ~650px use `sc` 0.75–0.85).
- Images (`fromImg`, `toImg`…): any PNG/JPG path. To use a real app logo: `sips -s format png -Z 512 "/Applications/<App>.app/Contents/Resources/<icon>.icns" --out logo.png` (the icon file name is in the app's Info.plist → CFBundleIconFile).

## Pack `tech` (product / tools / process)

| kind | what it shows | params | marks / durs |
|---|---|---|---|
| `hook` | **Logo swap** — a real logo gets slashed, then flips in 3D to another logo. The written hook. | `a`, `fromImg`, `fromName`, `toImg`, `toName`, `b` | `strike`, `flip`, `b` |
| `hookx` | Written hook card, two lines; optional key word lights up when said | `a`, `b` | `b` (optional) |
| `clock` | Dial: the hand sweeps a fraction of the dial (0.5 = «نص ساعة»), then a ring closes + check; texts switch on their words | `texts[]`, `turn` (0.5) | `texts[]`, `sweep`, `ready` |
| `plugin` | Two cartridges drop into a slot and light up (any two things that «plug in») | `title`, `items[2]`, `icons[2]` (`skills`/`agents`), `sub` | `c[2]`, `sub` |
| `prompt` | Chat box: a file chip drops in, the ask types itself, send is pressed | `text` | `file`, `type`, `send` · durs `typeDur` |
| `agents` | Five dormant nodes wake one after another along a wire | `title` | `go` |
| `cut` | **3D scissors** snip a filmstrip of the REAL frames around this cut; cut-out frames fall away, the strip closes (frames are picked automatically) | `t1`, `t2` | `t2`, `mark`, `sweep`, `close` · durs `sweepDur` |
| `wall` | Full screen: a counter runs to N while 200 tiny tiles, each a different motion, sweep in | `a`, `b` (number is 200 in the code — edit for others) | `b` · durs `fill` |
| `trans` | Three words, each entering with its own transition (wipe / spring tilt / typewriter) | `w0`, `w1`, `w2` | `w[3]` |
| `plat` | A 9:16 frame of the video stretches into 16:9 | `labels[2]` (Instagram/YouTube) | `yt` |
| `pull` | **Pull-back**: the video shrinks into a preview window and plays inside ITS OWN timeline (real thumbnails, scene blocks, captions, voice waveform, moving playhead). Must cover one whole take; build.py keyframes the clip to match. | `texts[]`, `side[]` (checklist), `side_at[]` (timeline time each side item was said — dropped if that part is cut) | `texts[]`, `side` |
| `ready` | Edit tracks assemble, counter stops at 97% + check | `texts[]` | `texts[]`, `start`, `ok` · durs `fillDur` |
| `dev` | One line types itself with a blinking cursor | `text` | durs `typeDur` |
| `cta` | A comment gets typed; a reply chip slides in | `title`, `bubble`, `reply` | `type`, `rep` |
| `steps` | A staircase: a dot climbs one step per beat («خطوة بخطوة») | `title` | `climb` · durs `climbDur` |

## Pack `story` (ideas / opinions / stories)

| kind | what it shows | params | marks |
|---|---|---|---|
| `hook` | Viewfinder brackets snap onto the key word | `a`, `b` | — |
| `grid` | A contact sheet fills to 100 | `label` | durs `fill` |
| `ask` | Question chips with icons, one per question | `rows[{icon: light/angle/dial, text}]` | `rows[]` |
| `cmp` | Two pictures: «his» works ✓, «mine» doesn't ✗ | `la`, `lb`, `no` | `b`, `x` |
| `chain` | People circles: small one gets hit, bigger ones behind | `l0`, `l1` | `hit`, `big` |
| `same` | Full screen: original vs copy, identical rows, empty dashed box «nothing of yours» | `title`, `rows[3]`, `empty` | `rows[3]`, `empty` |
| `you` | Full screen: stacked words land one by one (last one biggest) | `rows[]` | `rows[]` |
| `wall` | Full screen: 100 video tiles, the name strips wipe off | `title`, `title2` | `name`, `q` |

## Inspiration index
`assets/motion_library/catalog.tsv`: 234 Claude-made motion pieces from prompt-motion.com (id, title, author, tags, aspect). Open `https://prompt-motion.com/<id>` to read a technique, then build the scene in our own style. Never copy someone's piece; credit the idea when it's close.

## Writing a NEW scene
Add a `<div class="s" id="<kind>">` block + an `S.<kind> = {setup(o){…}, render(t,o){…}}` entry to a pack. `render(t)` must be a pure function of time (frames are rendered one by one). Readable at frame 0 if it opens the video. Keep content above y≈480 unless `full`.
