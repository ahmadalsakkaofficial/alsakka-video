# OPTIONAL: the same edit as an editable CapCut timeline (for people who want to tweak by hand). The MP4 from export.py doesn't need this.
#   python3 capcut_write.py <workdir> <edit> <project> <timeline>     (CapCut closed; the project + timeline must exist — an empty one is fine)
# Builds every track from the plan (takes + zoom keyframes, scenes, captions, transitions, SFX) and installs it into that timeline (backup first).
import json, os, sys, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
import capcut

W, EDIT, PROJ, TLN = sys.argv[1:5]
P = jload(f'{W}/plan_{EDIT}.json'); C = cfg(); REF = jload(f'{ASSETS}/capcut/ref.json')
def portable(o): return json.loads(json.dumps(o, ensure_ascii=False).replace('{CAPCUT}', CAPCUT_DATA).replace('{FONT}', C['caption_font']))
CAPT = portable(jload(f'{ASSETS}/capcut/captions.json')); TRL = portable(jload(f'{ASSETS}/capcut/transitions.json'))
ACC = [int(C['accent'][i:i + 2], 16) / 255 for i in (1, 3, 5)]
capcut.backup(PROJ, TLN); d = jload(capcut.draft_path(PROJ, TLN)); M = d.setdefault('materials', {})
for k in ['videos', 'audios', 'texts', 'speeds', 'canvases', 'placeholder_infos', 'sound_channel_mappings', 'vocal_separations', 'material_colors',
          'material_animations', 'beats', 'audio_fades', 'transitions', 'video_effects', 'effects']: M[k] = []
byid = {}
def add(kind, o): M[kind].append(o); byid[o['id']] = (kind, o); return o['id']
def mk(kind, **kw): o = copy.deepcopy(REF[kind]); o['id'] = U(); o.update(kw); return o
def clone_seg(s, mats):
    s = copy.deepcopy(s); s['id'] = U(); k, m = mats[s['material_id']]; m = copy.deepcopy(m); m['id'] = U(); add(k, m); s['material_id'] = m['id']; refs = []
    for r in s.get('extra_material_refs', []):
        if r in mats and mats[r][0] != 'transitions': kk, mm = mats[r]; mm = copy.deepcopy(mm); mm['id'] = U(); add(kk, mm); refs.append(mm['id'])
    s['extra_material_refs'] = refs; return s
def kf(prop, pts):
    return {'id': U(), 'material_id': '', 'property_type': prop, 'keyframe_list': [{'id': U(), 'curveType': 'Line', 'time_offset': int(t), 'left_control': {'x': 0.0, 'y': 0.0},
            'right_control': {'x': 0.0, 'y': 0.0}, 'values': [v], 'string_value': '', 'graphID': ''} for t, v in pts]}
def video_seg(path, a, n, src_us=0, volume=0.0, idx=8, has_audio=False):
    w, h, D = probe(path); mat = mk('video_mat', path=path, material_name=os.path.basename(path), width=w, height=h, duration=int(D * 1e6), type='video', has_audio=has_audio)
    mat['video_algorithm']['time_range'] = {'duration': US(n), 'start': src_us}; add('videos', mat)
    refs = [add(k, mk(k)) for k in ('speeds', 'placeholder_infos', 'canvases', 'material_animations', 'sound_channel_mappings', 'material_colors', 'vocal_separations')]
    M['speeds'][-1]['speed'] = 1.0; g = copy.deepcopy(REF['video_seg'])
    g.update(id=U(), material_id=mat['id'], extra_material_refs=refs, source_timerange={'duration': US(n), 'start': src_us}, target_timerange={'duration': US(a + n) - US(a), 'start': US(a)},
             speed=1.0, volume=volume, last_nonzero_volume=1.0, render_index=idx, track_render_index=0)
    g['clip']['scale'] = {'x': 1.0, 'y': 1.0}; g['clip']['transform'] = {'x': 0.0, 'y': 0.0}; g['common_keyframes'] = []; g['uniform_scale'] = {'on': True, 'value': 1.0}
    return g

# main track: takes with their zoom plan as keyframes (CapCut keyframe time = SOURCE time)
ms = []
for t in P['takes']:
    src = int(round(t['src'] * 1e6)); g = video_seg(t['path'], t['start'], t['frames'], src, volume=1.0, idx=0, has_audio=True); z = t['zoom']
    g['clip']['scale'] = {'x': z[0][1], 'y': z[0][1]}; g['clip']['transform']['y'] = z[0][2]
    g['common_keyframes'] = [kf('KFTypeScaleX', [(src + int(p[0] * 1e6), p[1]) for p in z])]
    if len({p[2] for p in z}) > 1: g['common_keyframes'].append(kf('KFTypePositionY', [(src + int(p[0] * 1e6), p[2]) for p in z]))
    ms.append(g)
for tr in P['transitions']:
    x = next((g for g in ms if g['target_timerange']['start'] + g['target_timerange']['duration'] == US(tr['at'])), None)
    if x and tr['name'] in TRL: tm = copy.deepcopy(TRL[tr['name']]); tm['id'] = U(); add('transitions', tm); x['extra_material_refs'].insert(min(2, len(x['extra_material_refs'])), tm['id'])
main = {'attribute': 0, 'flag': 0, 'id': U(), 'is_default_name': True, 'name': '', 'segments': ms, 'type': 'video'}
mo = [video_seg(f'{W}/overlays/{s["hash"]}.mov', s['at'], s['frames']) for s in P['scenes']]
MOT = {'attribute': 0, 'flag': 2, 'id': U(), 'is_default_name': False, 'name': 'موشن', 'segments': mo, 'type': 'video'}
CS = CAPT[P['caption_style']]; cm = {m['id']: (k, m) for kk in ('key', 'plain') for k, m in CS[kk]['mats']}; caps = []
for c in P['captions']:
    n = clone_seg(CS['key' if c['key'] else 'plain']['seg'], cm); m = byid[n['material_id']][1]; cc = json.loads(m['content'])
    white = [x for x in cc['styles'] if x['fill']['content']['solid']['color'] == [1, 1, 1]]; acc = [x for x in cc['styles'] if x['fill']['content']['solid']['color'] != [1, 1, 1]]
    sp = copy.deepcopy(white[0] if white else cc['styles'][0]); sk = copy.deepcopy(acc[0] if acc else cc['styles'][0])
    if not white: sp['fill']['content']['solid']['color'] = [1, 1, 1]; sp['size'] = sk['size'] / 1.35
    if not acc: sk['size'] = sp['size'] * 1.35
    sk['fill']['content']['solid']['color'] = ACC
    for st in (sp, sk):
        if 'font' in st: st['font']['path'] = C['caption_font']
    text = ' '.join(w[0] for w in c['words']); styles, pos = [], 0
    for w, _, _, key in c['words']:
        st = copy.deepcopy(sk if key else sp); st['range'] = [pos, pos + len(w)]; styles.append(st); pos += len(w)
        if pos < len(text): s2 = copy.deepcopy(sp); s2['range'] = [pos, pos + 1]; styles.append(s2); pos += 1
    cc['styles'] = styles; cc['text'] = text; m['content'] = json.dumps(cc, ensure_ascii=False); m['font_path'] = C['caption_font']
    for kk in ('recognize_text', 'words'): m.pop(kk, None)
    n['target_timerange'] = {'start': US(c['a']), 'duration': US(c['b']) - US(c['a'])}; n['clip']['transform']['y'] = round((960 - c['y']) / 960, 4); caps.append(n)
CAP = {'attribute': 0, 'flag': 1, 'id': U(), 'is_default_name': False, 'name': 'كابشن', 'segments': caps, 'type': 'text'}
sx = []
for x in P['sfx']:
    p = f'{ASSETS}/sfx/{x["name"]}.wav'; D = min(probe(p)[2], (P['dur'] - x['at']) / FPS)
    mat = mk('audio_mat', path=p, name=os.path.basename(p), duration=int(D * 1e6), type='extract_music', category_name='local'); add('audios', mat)
    refs = [add(k, mk(k)) for k in ('speeds', 'placeholder_infos', 'beats', 'sound_channel_mappings', 'vocal_separations')]; M['speeds'][-1]['speed'] = 1.0
    s = copy.deepcopy(REF['audio_track']['segments'][0])
    s.update(id=U(), material_id=mat['id'], extra_material_refs=refs, source_timerange={'duration': int(D * 1e6), 'start': 0}, target_timerange={'duration': int(D * 1e6), 'start': US(x['at'])}, volume=x['vol'], last_nonzero_volume=x['vol']); sx.append(s)
sx.sort(key=lambda s: s['target_timerange']['start'])
for a, b in zip(sx, sx[1:]):
    if a['target_timerange']['start'] + a['target_timerange']['duration'] > b['target_timerange']['start']: a['target_timerange']['duration'] = a['source_timerange']['duration'] = b['target_timerange']['start'] - a['target_timerange']['start']
d['tracks'] = [main, MOT, CAP] + ([{'attribute': 0, 'flag': 0, 'id': U(), 'is_default_name': False, 'name': 'مؤثرات', 'segments': sx, 'type': 'audio'}] if sx else [])
for ti, t in enumerate(d['tracks']):
    for s in t['segments']: s['track_render_index'] = ti
d['duration'] = US(P['dur']); d['canvas_config'] = {'ratio': 'original', 'width': 1080, 'height': 1920, 'background': None}
out = f'{W}/staging/{EDIT}/draft_info.json'; os.makedirs(os.path.dirname(out), exist_ok=True); jsave(out, d, True)
capcut.install(PROJ, TLN, out)
