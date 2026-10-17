# Step 1 of an edit: read the video(s), transcribe, measure the face.
#   python3 prep.py <workdir> <video> [<video> …] [--model medium] [--prompt "names, English terms they say"]
#   python3 prep.py <workdir> --capcut <project> <timeline> …     (optional: start from a CapCut timeline instead of files)
# Writes into <workdir>: takes.json (each file = one take until silence.py cuts it), voice48k.wav, words.json ([word, start, end] in seconds of the takes back to back),
# chins.json ({take: [[t, chin_y_0..1], ...]}), and prints the transcript per take.
import json, os, sys, subprocess, shutil, wave
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

def args():
    a = sys.argv[1:]; opt = {'model': 'medium', 'prompt': ''}
    while '--model' in a: k = a.index('--model'); opt['model'] = a[k + 1]; del a[k:k + 2]
    while '--prompt' in a: k = a.index('--prompt'); opt['prompt'] = a[k + 1]; del a[k:k + 2]
    return a[0], a[1:], opt

def whisper(wav, model, prompt, outdir):
    cmd = [tool('whisper'), wav, '--model', model, '--language', 'ar', '--word_timestamps', 'True', '--output_format', 'json', '--output_dir', outdir]
    if prompt: cmd += ['--initial_prompt', prompt]
    subprocess.run(cmd, capture_output=True, check=True)
    j = jload(os.path.join(outdir, os.path.splitext(os.path.basename(wav))[0] + '.json'))
    return [(w['word'].strip(), w['start'], w['end']) for s in j['segments'] for w in s['words'] if w['word'].strip()]

def rms_env(wav):        # 20 Hz loudness envelope
    import numpy as np
    w = wave.open(wav); x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768; sr = w.getframerate(); h = sr // 20
    n = len(x) // h; return np.sqrt((x[:n * h].reshape(n, h) ** 2).mean(1))

if __name__ == '__main__':
    W, src, opt = args(); os.makedirs(W, exist_ok=True)
    if src[0] == '--capcut':
        import capcut; P, T = src[1], src[2]
        shutil.copy(capcut.backup(P, T), os.path.join(W, 'orig_draft_info.json')); tk = capcut.takes(P, T); meta = dict(project=P, timeline=T)
    else:
        tk, at = [], 0.0
        for k, p in enumerate(src):
            p = os.path.abspath(os.path.expanduser(p)); assert os.path.exists(p), f'⛔ file not found: {p}'
            D = probe(p)[2]; tk.append(dict(i=k, path=p, src=0.0, dur=D, at=at)); at += D
        meta = dict(files=[t['path'] for t in tk])
    jsave(os.path.join(W, 'takes.json'), tk); jsave(os.path.join(W, 'meta.json'), meta)
    # timeline-order audio (works when takes come from several files)
    ff = tool('ffmpeg'); parts = []
    for k, t in enumerate(tk):
        p = os.path.join(W, f'_a{k}.wav'); parts.append(p)
        subprocess.run([ff, '-v', 'error', '-y', '-ss', str(t['src']), '-t', str(t['dur']), '-i', t['path'], '-vn', '-ac', '1', '-ar', '48000', p], check=True)
    lst = os.path.join(W, '_a.txt'); open(lst, 'w').write(''.join(f"file '{p}'\n" for p in parts))
    v48 = os.path.join(W, 'voice48k.wav'); cat = os.path.join(W, 'cat.wav')
    subprocess.run([ff, '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', v48], check=True)
    subprocess.run([ff, '-v', 'error', '-y', '-i', v48, '-ar', '16000', cat], check=True)
    for p in parts + [lst]: os.remove(p)
    print(f'⏳ transcribing {sum(t["dur"] for t in tk):.0f}s with whisper {opt["model"]} (slow on CPU: ~5-10× the length)…', flush=True)
    words = whisper(cat, opt['model'], opt['prompt'], W)
    # whisper sometimes skips a stretch silently: re-transcribe any gap > 1.5s that has speech energy
    env = rms_env(cat); thr = max(0.01, float(sorted(env)[len(env) // 3]) * 3)
    bounds = [0.0] + [w[2] for w in words]; nexts = [w[1] for w in words] + [len(env) / 20]
    for a, b in zip(bounds, nexts):
        if b - a > 1.5 and (env[int(a * 20):int(b * 20)] > thr).sum() > 15:
            gw = os.path.join(W, '_gap.wav'); subprocess.run([ff, '-v', 'error', '-y', '-ss', str(a), '-t', str(b - a), '-i', cat, gw], check=True)
            extra = [(x, s + a, e + a) for x, s, e in whisper(gw, opt['model'], opt['prompt'], W)]
            print(f'  ↺ re-transcribed gap {a:.1f}–{b:.1f}s: {" ".join(x for x, _, _ in extra)}'); words += extra
    words.sort(key=lambda w: w[1]); jsave(os.path.join(W, 'words.json'), words)
    # face: chin height per take every 0.25s (captions sit under it). macOS Vision via the compiled helper.
    face = os.path.join(CFG_DIR, 'bin/face'); chins = {}
    if os.path.exists(face):
        fd = os.path.join(CFG_DIR, 'faces_tmp'); shutil.rmtree(fd, ignore_errors=True); os.makedirs(fd)
        for k, t in enumerate(tk):
            subprocess.run([ff, '-v', 'error', '-y', '-ss', str(t['src']), '-t', str(t['dur']), '-i', t['path'], '-vf', 'fps=4,scale=540:960', f'{fd}/s{k:03d}_%04d.jpg'], check=True)
        out = subprocess.run([face] + sorted(os.path.join(fd, f) for f in os.listdir(fd)), capture_output=True, text=True).stdout
        for line in out.splitlines():
            p, *r = line.split(' ')
            if r and r[0] != 'none': n = os.path.basename(p); chins.setdefault(int(n[1:4]), []).append([(int(n[5:9]) - 1) * 0.25, float(r[3]), float(r[1])])
        shutil.rmtree(fd, ignore_errors=True)
    else: print('⚠️ face helper missing (setup) → captions use a safe default height')
    jsave(os.path.join(W, 'chins.json'), chins)
    print('\n── transcript per take (timeline seconds) ──')
    for k, t in enumerate(tk):
        ws = [w for w in words if t['at'] <= (w[1] + w[2]) / 2 < t['at'] + t['dur']]
        top = min((c[2] for c in chins.get(k, [])), default=None)
        print(f"[{k}] {t['at']:.2f}–{t['at'] + t['dur']:.2f}  ({len(ws)} words{', face top %.0fpx' % (top * 1920) if top else ''})  " + ' '.join(w[0] for w in ws))
