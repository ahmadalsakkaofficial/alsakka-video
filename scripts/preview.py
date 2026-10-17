# Preview sheet: every scene still (node render.js <workdir> <edit> --stills) composited over the real frame under it.
#   python3 preview.py <workdir> [edit]   → <workdir>/preview_<edit>.jpg   (look at it before rendering the full scenes)
import json, os, sys, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
W = sys.argv[1]; EDIT = sys.argv[2] if len(sys.argv) > 2 else 'edit'
ov = jload(f'{W}/ov_{EDIT}.json'); TK = jload(f'{W}/takes.json'); E = jload(f'{W}/{EDIT}.json')
if 'extends' in E: b = jload(f'{W}/{E["extends"]}'); b.update(E); E = b
ff = tool('ffmpeg'); outs = []
starts = {s['name']: s for s in E['scenes']}
for o in ov:
    s = starts[o['name']]
    for t in o.get('stills', [0]):
        png = f'{W}/prev/{o["name"]}_{t}.png'
        if not os.path.exists(png): continue
        k = s['take'] if s.get('take') is not None else next(i for i, x in enumerate(TK) if x['at'] <= s['at'] < x['at'] + x['dur'])
        st = TK[k]['src'] + (0 if s.get('take') is not None else s['at'] - TK[k]['at']) + t
        sc, ty = 1, 0
        if o['kind'] == 'pull':
            K = o['kf']; j = 0
            while j < len(K) - 2 and t > K[j + 1][0]: j += 1
            (t0, s0, y0), (t1, s1, y1) = K[j], K[j + 1]; u = min(1, max(0, (t - t0) / max(1e-6, t1 - t0))); sc = s0 + (s1 - s0) * u; ty = y0 + (y1 - y0) * u
        w, h = int(1080 * sc) // 2 * 2, int(1920 * sc) // 2 * 2; x, y = 540 - w // 2, int(960 - ty * 960 - h / 2)
        fr = f'{W}/prev/_bg.png'; out = png.replace('.png', '.jpg')
        subprocess.run([ff, '-v', 'error', '-y', '-ss', str(st), '-i', TK[k]['path'], '-vf', 'scale=1080:1920', '-frames:v', '1', fr], check=True)
        subprocess.run([ff, '-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=black:s=1080x1920:d=1', '-i', fr, '-i', png, '-filter_complex',
                        f'[1]scale={w}:{h}[v];[0][v]overlay={x}:{y}[b];[b][2]overlay,scale=360:640', '-frames:v', '1', out], check=True); outs.append(out)
n = len(outs); cols = 6; a = []
for x in outs: a += ['-i', x]
subprocess.run([ff, '-v', 'error', '-y', *a, '-filter_complex', ''.join(f'[{i}]' for i in range(n)) + f'xstack=inputs={n}:layout=' + '|'.join(f'{(i % cols) * 360}_{(i // cols) * 640}' for i in range(n)) + ':fill=black',
                '-q:v', '3', f'{W}/preview_{EDIT}.jpg'], check=True)
print('→', f'{W}/preview_{EDIT}.jpg', f'({n} frames)')
