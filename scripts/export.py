# Step 5: the finished video. Cut + zooms + transitions + scenes + captions + voice + SFX → one MP4 ready to post (1080×1920, 30fps).
#   python3 export.py <workdir> [edit]        (needs: build.py, node render.js <workdir> <edit>, node render.js <workdir> <edit> --captions)
#   → <workdir>/<edit>.mp4
import json, os, sys, subprocess, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

W = sys.argv[1]; EDIT = sys.argv[2] if len(sys.argv) > 2 else 'edit'
P = jload(f'{W}/plan_{EDIT}.json'); ff = tool('ffmpeg'); TMP = os.path.join(W, '_export'); shutil.rmtree(TMP, ignore_errors=True); os.makedirs(TMP)
run = lambda a: subprocess.run([ff, '-v', 'error', '-y'] + a, check=True)
cap = f'{W}/captions_{EDIT}.mov'; assert os.path.exists(cap), f'captions missing → node render.js {W} {EDIT} --captions'
for s in P['scenes']: assert os.path.exists(f'{W}/overlays/{s["hash"]}.mov'), f'scene {s["name"]} not rendered → node render.js {W} {EDIT}'

def pw(pts, col):           # piecewise-linear expression in t (seconds inside the take)
    e = f'{pts[-1][col]}'
    for p, q in reversed(list(zip(pts, pts[1:]))):
        e = f"if(lt(t,{q[0]}),{p[col]}+({q[col]}-({p[col]}))*(t-{p[0]})/{max(1e-6, q[0] - p[0])},{e})"
    return e

# transitions at cuts: 'Pull Out' / 'Shaky Inhale' = a quick zoom punch through the cut; 'Glare II' = a soft white flash
kick = {}; flash = []
for t in P['transitions']:
    if t['name'] == 'Glare II': flash.append(t['at'] / FPS)
    else: kick[t['at']] = t['name']

# 1 · every kept take: trimmed, filled to 9:16, zoomed per plan, on a black canvas (the pull-back shows black only under the overlay)
parts = []
for k, t in enumerate(P['takes']):
    d = t['frames'] / FPS; z = t['zoom']; S = pw(z, 1); TY = pw(z, 2)
    st, en = t['start'], t['start'] + t['frames']
    if en in kick: S = f"({S})*(1+0.12*clip((t-{d - 0.13})/0.13,0,1))"                         # punch out of the cut…
    if st in kick: S = f"({S})*(1+0.12*clip(1-t/0.2,0,1))"                                   # …and settle into the next take
    if st in kick and kick[st] == 'Shaky Inhale': TY = f"({TY})+0.012*sin(t*90)*clip(1-t/0.3,0,1)"
    fc = (f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps={FPS},setpts=PTS-STARTPTS,"
          f"scale=w='2*trunc(540*({S}))':h='2*trunc(960*({S}))':eval=frame[v];"
          f"[1:v][v]overlay=x='(W-w)/2':y='960-({TY})*960-h/2':eval=frame:shortest=1,format=yuv420p[o];"
          f"[0:a]aresample=48000,asetpts=PTS-STARTPTS,afade=t=in:d=0.012,afade=t=out:st={d - 0.015}:d=0.015[a]")
    out = f'{TMP}/t{k:03d}.mp4'; parts.append(out)
    run(['-ss', f"{t['src']:.4f}", '-t', f'{d:.4f}', '-i', t['path'], '-f', 'lavfi', '-i', f'color=black:s=1080x1920:r={FPS}', '-filter_complex', fc,
         '-map', '[o]', '-map', '[a]', '-frames:v', str(t['frames']), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '12', '-c:a', 'pcm_s16le', '-ar', '48000', out.replace('.mp4', '.mov')])
    parts[-1] = out.replace('.mp4', '.mov'); print(f'  take {k + 1}/{len(P["takes"])}', flush=True)
open(f'{TMP}/list.txt', 'w').write(''.join(f"file '{p}'\n" for p in parts))
base = f'{TMP}/base.mov'; run(['-f', 'concat', '-safe', '0', '-i', f'{TMP}/list.txt', '-c', 'copy', base])

# 2 · composite: scenes + captions on top, voice + sound effects mixed and brought to a normal loudness
ins = ['-i', base]; fc = []; last = '[0:v]'
if flash:
    br = '+'.join(f'0.55*max(0,1-abs(t-{x:.3f})/0.12)' for x in flash); fc.append(f'{last}eq=brightness=\'{br}\':eval=frame[vb]'); last = '[vb]'
n = 1
for s in sorted(P['scenes'], key=lambda s: s['at']):
    ins += ['-i', f'{W}/overlays/{s["hash"]}.mov']
    fc.append(f'[{n}:v]trim=end_frame={s["frames"]},setpts=PTS-STARTPTS+{s["at"] / FPS:.4f}/TB[s{n}];{last}[s{n}]overlay=eof_action=pass:format=auto[m{n}]'); last = f'[m{n}]'; n += 1
ins += ['-i', cap]; fc.append(f'[{n}:v]setpts=PTS-STARTPTS[cp];{last}[cp]overlay=eof_action=pass:format=auto,format=yuv420p[vout]'); n += 1
amix = ['[0:a]']
for x in P['sfx']:
    ins += ['-i', f'{ASSETS}/sfx/{x["name"]}.wav']; ms = int(x['at'] / FPS * 1000)
    fc.append(f'[{n}:a]aresample=48000,volume={x["vol"]},adelay={ms}|{ms}[x{n}]'); amix.append(f'[x{n}]'); n += 1
fc.append(f'{"".join(amix)}amix=inputs={len(amix)}:normalize=0:duration=first,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[aout]')
out = f'{W}/{EDIT}.mp4'
run(ins + ['-filter_complex', ';'.join(fc), '-map', '[vout]', '-map', '[aout]', '-frames:v', str(P['dur']), '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
           '-pix_fmt', 'yuv420p', '-r', str(FPS), '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', out])
shutil.rmtree(TMP, ignore_errors=True)
print(f'✓ {out} · {P["dur"] / FPS:.2f}s · {len(P["scenes"])} scenes · {len(P["captions"])} captions · {len(P["sfx"])} sfx')
