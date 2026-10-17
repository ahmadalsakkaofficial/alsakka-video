#!/bin/bash
# One-time setup on a Mac: ffmpeg, whisper, node + puppeteer-core, the face helper, and checks for Chrome and CapCut.
# Safe to run again: it only installs what's missing.

HERE="$(cd "$(dirname "$0")" && pwd)"; CFG="$HOME/.alsakka-video"; mkdir -p "$CFG/bin"
ok(){ printf "  ✅ %s\n" "$1"; }; miss(){ printf "  ❌ %s\n" "$1"; }
echo "── alsakka-video setup ──"
[ "$(uname)" = "Darwin" ] || { echo "⛔ This plugin works on macOS only (CapCut desktop + Apple Vision)."; exit 1; }

have(){ command -v "$1" >/dev/null 2>&1 || [ -x "/opt/homebrew/bin/$1" ] || [ -x "/usr/local/bin/$1" ] || [ -x "$HOME/.local/videotools/bin/$1" ]; }
if ! have brew && { ! have ffmpeg || ! have node; }; then
  echo "⛔ Homebrew is needed to install ffmpeg/node. Install it with the command on https://brew.sh then run setup again."; exit 1; fi
have ffmpeg || brew install ffmpeg; ok "ffmpeg"
have node || brew install node; ok "node $(node -v 2>/dev/null || true)"

PY=python3
if ! have whisper && ! ls "$HOME"/Library/Python/*/bin/whisper >/dev/null 2>&1; then
  echo "  … installing whisper (first time only, a few minutes)"; $PY -m pip install --user -q "numpy<2" openai-whisper; fi
ok "whisper"
$PY -c "import numpy" 2>/dev/null || $PY -m pip install --user -q "numpy<2"; ok "numpy"

if [ ! -d "$CFG/node_modules/puppeteer-core" ]; then (cd "$CFG" && { [ -f package.json ] || npm init -y >/dev/null 2>&1; } && npm install puppeteer-core@23.11.1 >/dev/null 2>&1); fi; [ -d "$CFG/node_modules/puppeteer-core" ] && ok "puppeteer-core (draws the scenes)" || miss "puppeteer-core failed to install (npm install puppeteer-core in ~/.alsakka-video)"

if [ ! -x "$CFG/bin/face" ]; then
  if command -v swiftc >/dev/null 2>&1; then swiftc -O "$HERE/face.swift" -o "$CFG/bin/face" 2>/dev/null && ok "face helper (caption height under the chin)" || miss "face helper failed to build — captions will use a safe default height"
  else miss "face helper needs Xcode Command Line Tools (xcode-select --install) — optional"; fi
else ok "face helper"; fi

ls /Applications | grep -qiE "Google Chrome|Microsoft Edge|Brave|Chromium" && ok "browser for drawing scenes" || miss "install Google Chrome (used to draw the motion scenes)"
[ -d "$HOME/Movies/CapCut/User Data/Projects/com.lveditor.draft" ] && ok "CapCut desktop (optional export)" || echo "  ➖ CapCut not installed — fine, only needed for the optional CapCut export"
[ -f "$CFG/config.json" ] || cp "$HERE/../assets/config.example.json" "$CFG/config.json"
echo "  ⚙️  settings: $CFG/config.json (fonts, accent color, sound level)"
echo "── done ──"
