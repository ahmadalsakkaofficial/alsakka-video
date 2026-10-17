# Shared helpers: paths, user config, time units, tool discovery.
import json, os, shutil, subprocess, uuid

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(PLUGIN, 'assets')
HOME = os.path.expanduser('~')
CFG_DIR = os.path.join(HOME, '.alsakka-video')
CFG_FILE = os.path.join(CFG_DIR, 'config.json')
CAPCUT_DATA = os.path.join(HOME, 'Movies/CapCut/User Data')
DRAFTS = os.path.join(CAPCUT_DATA, 'Projects/com.lveditor.draft')

FPS = 30
F = lambda s: int(round(s * FPS))                    # seconds → frame
US = lambda f: int(round(f * 1e6 / FPS))             # frame → microseconds (CapCut unit)
U = lambda: str(uuid.uuid4()).upper()

DEFAULT_CFG = {
    # caption + scene fonts (any .ttf/.otf on disk). Defaults are the bundled OFL Tajawal fonts.
    'caption_font': os.path.join(ASSETS, 'fonts/Tajawal-Black.ttf'),
    'display_font_black': os.path.join(ASSETS, 'fonts/Tajawal-Black.ttf'),
    'display_font_bold': os.path.join(ASSETS, 'fonts/Tajawal-Bold.ttf'),
    'text_font_bold': os.path.join(ASSETS, 'fonts/Tajawal-Bold.ttf'),
    'text_font_regular': os.path.join(ASSETS, 'fonts/Tajawal-Regular.ttf'),
    'accent': '#FFC928',        # key words + highlights
    'bg': '#0D1117',            # cards / full-screen scenes
    'sfx_volume': 0.05,         # phone voice ≈ 0.05 · camera/lav voice louder → 0.2
    'look_timeline': None,      # optional: [project, timeline] whose filter/effect tracks are copied over the whole video
}

def cfg():
    c = dict(DEFAULT_CFG)
    if os.path.exists(CFG_FILE): c.update({k: v for k, v in json.load(open(CFG_FILE)).items() if v is not None})   # null = keep the bundled default
    return c

def tool(name):
    """ffmpeg / ffprobe / whisper / node: PATH first, then the usual install spots."""
    p = shutil.which(name)
    if p: return p
    for d in ('/opt/homebrew/bin', '/usr/local/bin', os.path.join(HOME, '.local/videotools/bin'), os.path.join(HOME, 'Library/Python/3.9/bin'),
              os.path.join(HOME, 'Library/Python/3.11/bin'), os.path.join(HOME, 'Library/Python/3.12/bin')):
        if os.path.exists(os.path.join(d, name)): return os.path.join(d, name)
    raise SystemExit(f'⛔ {name} not found — run the setup skill first')

def probe(path):
    r = json.loads(subprocess.run([tool('ffprobe'), '-v', 'error', '-show_entries', 'format=duration:stream=width,height,codec_type', '-of', 'json', path],
                                  capture_output=True, text=True).stdout)
    v = next((s for s in r['streams'] if s.get('codec_type') == 'video'), {})
    return v.get('width'), v.get('height'), float(r['format']['duration'])

def capcut_running():
    return bool(subprocess.run(['pgrep', '-ix', 'CapCut'], capture_output=True).stdout)

def jload(p): return json.load(open(p))
def jsave(p, o, compact=False):
    with open(p, 'w') as f: f.write(json.dumps(o, ensure_ascii=False, separators=(',', ':')) if compact else json.dumps(o, ensure_ascii=False, indent=1))
