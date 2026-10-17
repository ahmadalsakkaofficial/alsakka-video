# CapCut project tool.
#   python3 capcut.py list                              → projects (newest first) and their timelines
#   python3 capcut.py takes   <project> <timeline>      → the main-track clips (JSON): source file + source/target ranges
#   python3 capcut.py backup  <project> <timeline>      → copy of the timeline's draft into ~/.alsakka-video/backups
#   python3 capcut.py dup     <project> <timeline> <new name> [...]   → duplicate a timeline (prints new ids)
#   python3 capcut.py install <project> <timeline> <staged draft_info.json>   → put a built draft into the timeline (CapCut must be closed)
import json, os, sys, shutil, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

def project_dir(p): return os.path.join(DRAFTS, p)
def timelines(p):
    """[(name, id)] — multi-timeline projects keep Timelines/project.json; older ones are one root draft."""
    pj = os.path.join(project_dir(p), 'Timelines/project.json')
    if not os.path.exists(pj): return [('(main)', None)]
    return [(t['name'], t['id']) for t in jload(pj)['timelines'] if not t.get('is_marked_delete')]
def main_id(p):
    pj = os.path.join(project_dir(p), 'Timelines/project.json')
    return jload(pj).get('main_timeline_id') if os.path.exists(pj) else None
def tl_id(p, name):
    for n, i in timelines(p):
        if n == name or i == name: return i
    raise SystemExit(f'⛔ timeline "{name}" not in project {p}: {[n for n, _ in timelines(p)]}')
def draft_path(p, name):
    i = tl_id(p, name)
    return os.path.join(project_dir(p), 'Timelines', i, 'draft_info.json') if i else os.path.join(project_dir(p), 'draft_info.json')

def takes(p, name):
    d = jload(draft_path(p, name)); vids = {v['id']: v for v in d['materials']['videos']}
    main = next(t for t in d['tracks'] if t['type'] == 'video')
    return [dict(i=k, path=vids[s['material_id']]['path'], src=s['source_timerange']['start'] / 1e6, dur=s['target_timerange']['duration'] / 1e6,
                 at=s['target_timerange']['start'] / 1e6) for k, s in enumerate(main['segments'])]

def backup(p, name):
    src = draft_path(p, name); d = os.path.join(CFG_DIR, 'backups', p, (name or 'main').replace('/', '_'), time.strftime('%Y%m%d-%H%M%S'))
    os.makedirs(d, exist_ok=True); shutil.copy(src, d); print('backup →', d); return os.path.join(d, 'draft_info.json')

def dup(p, name, new_names):
    assert not capcut_running(), '⛔ close CapCut first'
    P = project_dir(p); src = tl_id(p, name); assert src, 'this project has a single timeline — duplicate it inside CapCut once first'
    pjf = os.path.join(P, 'Timelines/project.json'); lyf = os.path.join(P, 'timeline_layout.json')
    pj = jload(pjf); lay = jload(lyf) if os.path.exists(lyf) else None; out = {}
    for nn in new_names:
        assert nn not in [t['name'] for t in pj['timelines']], f'{nn} already exists'
        nid = U(); shutil.copytree(os.path.join(P, 'Timelines', src), os.path.join(P, 'Timelines', nid))
        for f in ('draft_info.json', 'draft_info.json.bak', 'template-2.tmp'):
            fp = os.path.join(P, 'Timelines', nid, f)
            if os.path.exists(fp):
                try: d = jload(fp); d['id'] = nid; jsave(fp, d, True)
                except Exception: pass
        now = int(time.time() * 1e6); t0 = next(t for t in pj['timelines'] if t['id'] == src)
        pj['timelines'].append(dict(t0, id=nid, name=nn, create_time=now, update_time=now))
        if lay: lay['dockItems'][0]['timelineIds'].append(nid); lay['dockItems'][0].setdefault('timelineNames', []).append(nn)
        out[nn] = nid; print(nn, nid)
    jsave(pjf, pj, True); shutil.copy(pjf, pjf + '.bak')
    if lay: jsave(lyf, lay, True)
    return out

def install(p, name, staged):
    assert not capcut_running(), '⛔ close CapCut first, then run install again'
    i = tl_id(p, name); d = jload(staged)
    if i: d['id'] = i
    targets = [draft_path(p, name), draft_path(p, name) + '.bak']
    if i:
        tmp = os.path.join(project_dir(p), 'Timelines', i, 'template-2.tmp')
        if os.path.exists(tmp): targets.append(tmp)
        if i == main_id(p): targets += [os.path.join(project_dir(p), 'draft_info.json')]       # single-timeline style projects read the root copy
    for t in targets: jsave(t, d, True)
    r = jload(targets[0]); print('installed →', name, '·', round(r['duration'] / 1e6, 2), 's ·', [(t.get('name') or t['type'], len(t['segments'])) for t in r['tracks']])

if __name__ == '__main__':
    a = sys.argv[1:]
    if not a or a[0] == 'list':
        ps = sorted([x for x in os.listdir(DRAFTS) if os.path.isdir(project_dir(x)) and not x.startswith('.')], key=lambda x: -os.path.getmtime(project_dir(x)))
        for x in ps[:20]: print(x, '→', ', '.join(n for n, _ in timelines(x)))
    elif a[0] == 'takes': print(json.dumps(takes(a[1], a[2]), ensure_ascii=False, indent=1))
    elif a[0] == 'backup': backup(a[1], a[2])
    elif a[0] == 'dup': dup(a[1], a[2], a[3:])
    elif a[0] == 'install': install(a[1], a[2], a[3])
