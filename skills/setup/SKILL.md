---
name: setup
description: تجهيز الجهاز أول مرة للبلجن — بيثبّت ffmpeg و whisper و node وأداة قياس الوجه، وبيتأكد من Chrome. Use when the user says "جهّز البلجن"، "setup"، "أول مرة"، or when another skill of this plugin reports a missing tool.
---

# Setup (once per Mac)

1. Tell the user in one line what will be installed and that it takes a few minutes the first time.
2. Run: `bash "${CLAUDE_PLUGIN_ROOT}/scripts/setup.sh"` (run it in the background if whisper still needs installing — it downloads ~1-2 GB of model on first transcription).
3. Read the ✅/❌ list back to them. For each ❌ give the one fix the script printed:
   - Homebrew missing → they paste the install command from https://brew.sh in Terminal (it asks for their Mac password — they do it, not you), then run setup again.
   - Xcode tools missing → optional; `xcode-select --install` (they confirm the dialog). Without it captions use a safe fixed height.
   - Chrome missing → they install it. (CapCut is only needed for the optional CapCut export.)
4. Optional settings in `~/.alsakka-video/config.json` (only if they ask): `accent` / `bg` colors, `caption_font` (+ the four display/text fonts) = path to any .ttf/.otf they own, `sfx_volume` (0.05 phone audio, ~0.2 camera/lav audio).
