# Step 1b (only for a RAW, uncut video): remove the silences between phrases.
#   python3 silence.py <workdir> [--gap 0.45] [--pad 0.12]
# Splits every take at pauses longer than --gap (from the word timings), trims each piece in the quietest spot near its edges,
# and rewrites the workdir's orig_draft_info.json / takes.json / words.json / chins.json so the rest of the pipeline sees the cut takes.
# Nothing is written to CapCut here; build.py + capcut.py install do that.
import json, os, sys, copy, wave
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
import numpy as np

a = sys.argv[1:]; W = a[0]; GAP = float(a[a.index('--gap') + 1]) if '--gap' in a else 0.45; PAD = float(a[a.index('--pad') + 1]) if '--pad' in a else 0.12
HAS_CC = os.path.exists(f'{W}/orig_draft_info.json'); d = jload(f'{W}/orig_draft_info.json') if HAS_CC else None; tk = jload(f'{W}/takes.json'); words = jload(f'{W}/words.json'); chins = {int(k): v for k, v in jload(f'{W}/chins.json').items()}
w = wave.open(f'{W}/voice48k.wav'); x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768; SR = w.getframerate()
def quietest(lo, hi):            # timeline seconds → time of lowest 20ms energy inside [lo, hi]
    ts = np.arange(max(0, lo), max(lo + 0.02, hi), 0.01)
    e = [np.sqrt(np.mean(x[int(t * SR):int(t * SR) + 960] ** 2) + 1e-12) for t in ts]; return float(ts[int(np.argmin(e))])

main = next(t for t in d['tracks'] if t['type'] == 'video') if HAS_CC else None; old = main['segments'] if HAS_CC else None
by = {m['id']: (k, m) for k, v in d['materials'].items() if isinstance(v, list) for m in v if isinstance(m, dict) and 'id' in m} if HAS_CC else {}
pieces = []                      # (old take index, timeline start, timeline end)
for k, t in enumerate(tk):
    ws = [w_ for w_ in words if t['at'] <= (w_[1] + w_[2]) / 2 < t['at'] + t['dur']]
    if not ws: continue
    runs = [[ws[0]]]
    for w_ in ws[1:]:
        gap = w_[1] - runs[-1][-1][2]
        if gap > GAP or (runs[-1][-1][0].endswith(('.', '؟', '?', '!')) and gap > 0.12): runs.append([w_])     # also split at sentence ends → retakes become their own takes
        else: runs[-1].append(w_)
    for r in runs:
        s = quietest(r[0][1] - PAD - 0.1, r[0][1] - 0.02); e = quietest(r[-1][2] + 0.02, r[-1][2] + PAD + 0.12)
        pieces.append((k, max(t['at'], s), min(t['at'] + t['dur'], e)))
segs, ntk, nwords, nch, o = [], [], [], {}, 0
for j, (k, s, e) in enumerate(pieces):
    src0 = int((tk[k]['src'] + s - tk[k]['at']) * 1e6); fs, fe = F(s), F(e); L = fe - fs
    ntk.append(dict(i=j, path=tk[k]['path'], src=src0 / 1e6, dur=L / FPS, at=o / FPS))
    nwords += [[w_[0], w_[1] - s + o / FPS, w_[2] - s + o / FPS] for w_ in words if s <= (w_[1] + w_[2]) / 2 < e]
    nch[j] = [[c[0] - (s - tk[k]['at']), *c[1:]] for c in chins.get(k, []) if s - tk[k]['at'] - 0.3 <= c[0] <= e - tk[k]['at'] + 0.3]
    o += L
    if not HAS_CC: continue
    g = copy.deepcopy(old[k]); g['id'] = U(); refs = []
    for r in g.get('extra_material_refs', []):
        if r in by and by[r][0] != 'transitions':
            kk, mm = by[r]; mm = copy.deepcopy(mm); mm['id'] = U(); d['materials'][kk].append(mm); refs.append(mm['id'])
    g['extra_material_refs'] = refs
    oo = US(F(ntk[-1]['at']))
    g['source_timerange'] = {'start': src0, 'duration': US(L)}; g['target_timerange'] = {'start': oo, 'duration': US(L)}
    g['common_keyframes'] = []; segs.append(g)
if HAS_CC: main['segments'] = segs; d['duration'] = US(o)
# the voice file must follow the new cut too
import subprocess
ff = tool('ffmpeg'); fc = ''.join(f'[0:a]atrim={s}:{s + (F(e) - F(s)) / FPS},asetpts=PTS-STARTPTS[a{i}];' for i, (_, s, e) in enumerate(pieces)) + ''.join(f'[a{i}]' for i in range(len(pieces))) + f'concat=n={len(pieces)}:v=0:a=1[o]'
subprocess.run([ff, '-v', 'error', '-y', '-i', f'{W}/voice48k.wav', '-filter_complex', fc, '-map', '[o]', f'{W}/_v.wav'], check=True); os.replace(f'{W}/_v.wav', f'{W}/voice48k.wav')
if HAS_CC: jsave(f'{W}/orig_draft_info.json', d, True)
jsave(f'{W}/takes.json', ntk); jsave(f'{W}/words.json', nwords); jsave(f'{W}/chins.json', nch)
before = sum(t['dur'] for t in tk)
print(f'✂️ {before:.1f}s → {o / FPS:.1f}s · {len(pieces)} pieces (pauses > {GAP}s removed)\n')
for t in ntk:
    ws = [w_ for w_ in nwords if t['at'] <= (w_[1] + w_[2]) / 2 < t['at'] + t['dur']]
    print(f"[{t['i']}] {t['at']:.2f}–{t['at'] + t['dur']:.2f}  " + ' '.join(w_[0] for w_ in ws))
