# Step 3: turn edit.json into ONE plan of the whole video (cut, zooms, scenes, captions, transitions, sounds).
#   python3 build.py <workdir> [edit.json]
#     → <workdir>/ov_<edit>.json    scenes for render.js
#     → <workdir>/plan_<edit>.json  everything export.py (MP4) and capcut_write.py (optional CapCut timeline) need
# All times in edit.json are seconds as prep.py / silence.py printed them (takes back to back, before your cut).
import json, sys, copy, os, subprocess, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

W = sys.argv[1]
EF = os.path.join(W, sys.argv[2] if len(sys.argv) > 2 else 'edit.json'); EDIT = os.path.splitext(os.path.basename(EF))[0]
E = jload(EF)
if 'extends' in E: base = jload(os.path.join(W, E['extends'])); base.update({k: v for k, v in E.items() if k != 'extends'}); E = base
C = cfg(); TK = jload(f'{W}/takes.json'); WORDS = [tuple(w) for w in jload(f'{W}/words.json')]
CH = {int(k): v for k, v in jload(f'{W}/chins.json').items()}

# ── takes kept, back to back (frame-aligned) ──
KEEP = E['keep']; AT_END = set(E.get('hooks_at_end', []))           # alternate hooks appended after the last word (Trial Reel material)
offs = {}; o = 0
for i in KEEP:
    a, b = F(TK[i]['at']), F(TK[i]['at'] + TK[i]['dur']); offs[i] = (a, b, o); o += b - a
DUR = o; MAIN = [i for i in KEEP if i not in AT_END]
def take_at(t): return next((i for i in range(len(TK)) if F(TK[i]['at']) <= F(t) < F(TK[i]['at'] + TK[i]['dur'])), len(TK) - 1)
def inkeep(t): return take_at(t) in KEEP
def N(t, take=None):                     # old seconds → new frame
    i = take if take is not None else take_at(t); a, b, n = offs[i]; return n + min(max(F(t), a), b) - a

# ── captions: shown text per take; '^2' = one word over 2 whisper tokens, '~' = space inside one token, '|' = caption break ──
KEY = set(E.get('key', [])); STYLE = E.get('caption_style', 'default'); MXW = {'default': 6, 'box': 5, 'big': 4, 'clean': 5}[STYLE]
SMALL = {'ما', 'من', 'في', 'مع', 'كل', 'مو', 'بس', 'على', 'عم', 'شو', 'أنا', 'وإذا', 'إني', 'رح', 'أي', 'اللي', 'وبعد', 'هاد', 'و', 'يا', 'لا', 'عن', 'إلى', 'لـ'}
groups = []
for i in KEEP:
    a, b, n = offs[i]; ws = [w for w in WORDS if a <= F((w[1] + w[2]) / 2) < b]
    txt = E.get('captions', {}).get(str(i)) or ' | '.join(w[0] for w in ws)
    phs = []
    for ph in txt.split(' | '):
        t = ph.split(); nc = 1 if len(t) <= MXW else -(-len(t) // (MXW - 1)); cuts = [round(len(t) * k / nc) for k in range(nc + 1)]
        ch = [t[cuts[k]:cuts[k + 1]] for k in range(nc)]
        for k in range(len(ch) - 1):
            while len(ch[k]) > 1 and ch[k][-1].replace('^2', '') in SMALL: ch[k + 1].insert(0, ch[k].pop())
        phs += [' '.join(c) for c in ch if c]
    k = 0
    for ph in phs:
        g = []
        for tok in ph.split():
            m = 2 if tok.endswith('^2') else 1; disp = tok.replace('^2', '').replace('~', ' ').rstrip('.،,')
            seg = ws[k:k + m]; k += m
            assert seg, f'take {i}: captions have more words than whisper heard ({len(ws)}): {[w[0] for w in ws]}'
            g.append((disp, n + max(0, F(seg[0][1]) - a), n + min(b, F(seg[-1][2])) - a))
        groups.append((i, g))
    assert k == len(ws), f'take {i}: {k} caption tokens vs {len(ws)} whisper words: {[w[0] for w in ws]}'

# ── scenes ──
SC = [dict(s) for s in E.get('scenes', []) if (s.get('take') if s.get('take') is not None else take_at(s['at'])) in KEEP]
def stake(s): return s['take'] if s.get('take') is not None else take_at(s['at'])
def span(s):
    tk = stake(s); a = offs[tk][2] if s.get('take') is not None else N(s['at'])
    end = min(s['to'], TK[tk]['at'] + TK[tk]['dur']) if 'to' in s else TK[tk]['at'] + TK[tk]['dur']; return a, N(end, tk)
FULL = [span(s) for s in SC if s.get('full')]
PULL = next((s for s in SC if s['kind'] == 'pull'), None); PULL_TAKE = stake(PULL) if PULL else None
SMIN, TYMAX = 0.46, 0.375
def ease(x): return 1 - (1 - x) ** 3
def pull_kf(d):          # one piecewise-linear curve drives BOTH the clip and the overlay's window
    pts = [(0.0, 1.0, 0.0)]
    for k in range(7): u = ease(k / 6); pts.append((0.10 + 0.5 * k / 6, 1 + (SMIN - 1) * u, TYMAX * u))
    for k in range(7): u = ease(k / 6); pts.append((d - 0.48 + 0.42 * k / 6, SMIN + (1 - SMIN) * u, TYMAX * (1 - u)))
    pts.append((d, 1.0, 0.0)); return pts
def frame(path, t, out, w=540, h=960):
    if not os.path.exists(out): subprocess.run([tool('ffmpeg'), '-v', 'error', '-y', '-ss', str(max(0, t)), '-i', path, '-vf', f'scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}', '-frames:v', '1', out], check=True)
    return 'file://' + out
os.makedirs(f'{W}/stills', exist_ok=True)

# ── zoom plan per take: [[t_rel_s, scale, ty]] (ty: +1 = move up half a frame). Linear between points. ──
def chin(i): return max([c[1] for c in CH.get(i, [])] or [0.62])
def chin_shift(i, sc): return round((sc - 1) * (chin(i) * 1920 - 960) / 960, 4)     # keeps the chin where it was
PUNCH = {int(k): v for k, v in E.get('punch', {}).items()}; ZOOM = {}
for j, i in enumerate(KEEP):
    d = (offs[i][1] - offs[i][0]) / FPS
    if i == PULL_TAKE: ZOOM[i] = [list(p) for p in pull_kf(d)]; continue
    if j == 0 or i in AT_END: ZOOM[i] = [[0, 1.14, 0], [0.1, 1.09, 0], [0.2, 1.05, 0], [0.3, 1.02, 0], [0.4, 1.005, 0], [0.5, 1.0, 0], [d, 1.0, 0]]; continue
    a, b = PUNCH.get(i, (1.0, 1.05) if j % 2 else (1.08, 1.08)); ZOOM[i] = [[0, a, 0], [d, b, 0]]
for t, z in E.get('kicks', []):        # quick zoom kick on a strong word: everything after it × z
    if not inkeep(t) or take_at(t) == PULL_TAKE: continue
    i = take_at(t); rel = (N(t) - offs[i][2]) / FPS; P = ZOOM[i]
    val = lambda T: next((p[1] + (q[1] - p[1]) * (T - p[0]) / max(1e-6, q[0] - p[0]) for p, q in zip(P, P[1:]) if p[0] <= T <= q[0]), P[-1][1])
    ZOOM[i] = [p for p in P if p[0] < rel - 0.066] + [[rel - 0.066, val(rel - 0.066), 0], [rel + 0.066, val(rel + 0.066) * z, 0]] + [[p[0], p[1] * z, 0] for p in P if p[0] > rel + 0.066]
for i in KEEP:
    if i != PULL_TAKE:
        sh = chin_shift(i, min(p[1] for p in ZOOM[i])); ZOOM[i] = [[round(p[0], 4), round(p[1], 4), sh] for p in ZOOM[i]]
def zoom_at(f):
    i = next((i for i in KEEP if offs[i][2] <= f < offs[i][2] + offs[i][1] - offs[i][0]), KEEP[-1]); T = (f - offs[i][2]) / FPS; P = ZOOM[i]
    for p, q in zip(P, P[1:]):
        if p[0] <= T <= q[0]: u = (T - p[0]) / max(1e-6, q[0] - p[0]); return i, p[1] + (q[1] - p[1]) * u, p[2] + (q[2] - p[2]) * u
    return i, P[-1][1], P[-1][2]

# ── caption timing + height (one height per take: worst chin + 210px, kept 1150–1480; full-screen scenes → 1420) ──
def chin_y(f):
    i, s, ty = zoom_at(f); lt = (f - offs[i][2]) / FPS
    near = [c[1] for c in CH.get(i, []) if abs(c[0] - (lt + F(TK[i]['at']) / FPS - offs[i][0] / FPS)) <= 0.3] or [chin(i)]
    return 960 + (max(near) * 1920 - 960) * s - ty * 960
TAKE_Y = {}; caps = []
for gi, (i, gw) in enumerate(groups):
    a = gw[0][1]; nb = groups[gi + 1][1][0][1] if gi + 1 < len(groups) else DUR
    if any(x <= (a + nb) // 2 < z for x, z in FULL): continue
    TAKE_Y[i] = max(TAKE_Y.get(i, 0), min(max(max(chin_y(f) for f in range(a, max(a + 1, min(nb, a + F(2.5))), 3)) + 210, 1150), 1480))
for gi, (i, gw) in enumerate(groups):
    a = max(gw[0][1], F(0.5)) if gi == 0 else gw[0][1]
    b = groups[gi + 1][1][0][1] if gi + 1 < len(groups) else DUR
    if gi + 1 < len(groups): b = min(b, max(gw[-1][2] + F(0.6), a + 6))
    nxt = KEEP[KEEP.index(i) + 1] if KEEP.index(i) + 1 < len(KEEP) else None
    if nxt in AT_END: b = min(b, offs[i][2] + offs[i][1] - offs[i][0])          # appended hooks start clean
    if b <= a: continue
    full = any(x <= (a + b) // 2 < z for x, z in FULL)
    caps.append(dict(a=a, b=b, y=1420 if full else TAKE_Y.get(i, 1400), words=[[w, x, y, w in KEY] for w, x, y in gw], key=any(w in KEY for w, _, _ in gw)))

# ── transitions at take changes (≥1.2s both sides, ≥5s apart, not around full-screen scenes or appended hooks) ──
TRN = E.get('transitions', ['Pull Out', 'Glare II']); trans = []; last = -9e9
for x, y in zip(KEEP, KEEP[1:]):
    cut = offs[y][2]
    if not TRN or (offs[x][1] - offs[x][0]) < F(1.2) or (offs[y][1] - offs[y][0]) < F(1.2) or cut - last < F(5) or y in AT_END: continue
    if any(a - 6 <= cut <= b + 6 for a, b in FULL): continue
    trans.append(dict(at=cut, name=TRN[len(trans) % len(TRN)])); last = cut

# ── sound effects ──
VOL = C['sfx_volume']
sfx = [dict(name=x[0], at=max(0, N(x[1])), vol=x[2] if len(x) > 2 else round(VOL * (1.2 if x[0].startswith(('whoosh', 'thud')) else 1), 3)) for x in E.get('sfx', []) if inkeep(x[1])]

# ── scenes for render.js ──
ov = []
for s in SC:
    a, b = span(s); o = {k: v for k, v in s.items() if k not in ('at', 'to', 'take', 'durs')}; o['sc'] = s.get('sc', 1); o['dur'] = (b - a) / FPS
    o['pack'] = s.get('pack', 'tech'); o['brand'] = {'acc': C['accent'], 'bg': C['bg']}
    o['marks'] = {k: ([(N(x) - a) / FPS for x in v] if isinstance(v, list) else (N(v) - a) / FPS) for k, v in s.get('marks', {}).items()}
    o['marks'].update(s.get('durs', {}))
    for k, v in list(o.items()):
        if k.endswith('Img') and isinstance(v, str) and not v.startswith('file://'): o[k] = 'file://' + os.path.abspath(os.path.join(W, os.path.expanduser(v)))
    tk = stake(s); T = TK[tk]
    if s['kind'] == 'cut' and 'strip' not in s:        # REAL frames around this cut: kept ones stay, cut-out ones fall away
        same = [TK[i] for i in KEEP if TK[i]['path'] == T['path']]; ts = [max(0, T['src'] - 12) + 1.6 * j for j in range(10)]
        o['strip'] = [frame(T['path'], t_, f'{W}/stills/strip_{tk}_{j}.jpg', 180, 320) for j, t_ in enumerate(ts)]
        o['quiet'] = [not any(x['src'] <= t_ < x['src'] + x['dur'] for x in same) for t_ in ts]
    if s['kind'] == 'plat' and 'img' not in s: o['img'] = frame(T['path'], T['src'] + T['dur'] / 2, f'{W}/stills/plat_{tk}.jpg')
    if s['kind'] == 'pull':
        ML = sum(offs[i][1] - offs[i][0] for i in MAIN) / FPS; o.update(main=ML, now=a / FPS, kf=pull_kf(o['dur']), smin=SMIN)
        o['thumbs'] = [frame(TK[i]['path'], TK[i]['src'] + min(1, TK[i]['dur'] / 2), f'{W}/stills/tl_{i}.jpg', 90, 160) for i in MAIN][:12]
        o['scenes'] = [(span(x)[0] / FPS, span(x)[1] / FPS, x['name']) for x in SC if span(x)[0] / FPS < ML]
        o['caps'] = [(c['a'] / FPS, c['b'] / FPS) for c in caps if c['a'] / FPS < ML]
        import wave, numpy as np
        w = wave.open(f'{W}/voice48k.wav'); x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768; h = w.getframerate() // 20
        env = np.sqrt((x[:len(x) // h * h].reshape(-1, h) ** 2).mean(1)); mx = float(env.max()) or 1; wv = []
        for j in range(170):
            tn = F(ML * j / 170); i = next(i for i in MAIN if offs[i][2] <= tn < offs[i][2] + offs[i][1] - offs[i][0])
            old = (offs[i][0] + tn - offs[i][2]) / FPS; wv.append(round(min(1, float(env[min(len(env) - 1, int(old * 20))]) / mx * 1.6), 3))
        o['wave'] = wv
        o['side'] = [x for x, t_ in zip(s.get('side', []), s.get('side_at', [None] * 99)) if t_ is None or inkeep(t_)]
    o['stills'] = [round(o['dur'] * 0.6, 2)]
    o['hash'] = hashlib.md5(json.dumps({k: v for k, v in o.items() if k != 'stills'}, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]
    o['at'] = a; ov.append(o)
jsave(f'{W}/ov_{EDIT}.json', ov)
plan = dict(edit=EDIT, dur=DUR, fps=FPS, caption_style=STYLE, accent=C['accent'], timeline=E.get('timeline'), look=E.get('look', True),
            takes=[dict(i=i, path=TK[i]['path'], src=TK[i]['src'] + (offs[i][0] - F(TK[i]['at'])) / FPS, start=offs[i][2], frames=offs[i][1] - offs[i][0], zoom=ZOOM[i], end_hook=i in AT_END) for i in KEEP],
            scenes=[dict(name=o['name'], hash=o['hash'], at=o['at'], frames=round(o['dur'] * FPS), full=bool(o.get('full'))) for o in ov],
            captions=caps, transitions=trans, sfx=sfx)
jsave(f'{W}/plan_{EDIT}.json', plan)
print(f'{EDIT}: {DUR / FPS:.2f}s · {len(KEEP)} takes · {len(ov)} scenes · {len(caps)} captions · {len(trans)} transitions · {len(sfx)} sfx')
for o in ov: print(f"   {o['name']:<10} {o['kind']:<8} {o['at'] / FPS:6.2f}s +{o['dur']:.2f}s", {k: (round(v, 2) if isinstance(v, float) else v) for k, v in o['marks'].items()})
inner = {o['at'] + round(x * FPS) for o in ov for k, v in o['marks'].items() if not k.endswith(('Dur', 'fill')) for x in (v if isinstance(v, list) else [v]) if 0 < x < o['dur']}   # moments inside scenes count as changes
cuts = sorted({0, DUR} | {offs[i][2] for i in KEEP} | {o['at'] for o in ov} | inner | {N(t) for t, _ in E.get('kicks', []) if inkeep(t)})
long = [(round(x / FPS, 1), round(y / FPS, 1)) for x, y in zip(cuts, cuts[1:]) if y - x > F(4)]
if long: print('⚠️ 4-second rule: nothing changes in', long, '→ add a scene, a kick or a punch-in there')
