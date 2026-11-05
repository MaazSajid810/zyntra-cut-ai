"""Read-only checks of actual saved exports. Does not process or edit projects."""
import json
from pathlib import Path

import av
from backend import media,store

results=[]
history=[]
for p in store.all_projects():
    if p['status']=='error':
        history.append({'project_id':p['id'],'name':p['name'],'error':p.get('error')})
    for c in p['clips']:
        if c['status']!='ready':
            continue
        try:
            path=store.DATA/p['id']/c['file']
            info=media.probe(path)
            assert abs(info['duration']-(c['end']-c['start']))<.5, 'Duration differs from the selected range'
            assert info['has_audio']==(p['has_audio'] and c.get('voice_effect')!='mute'),'Audio stream does not match settings'
            with av.open(str(path)) as container:
                frame=next(container.decode(video=0))
                assert frame.width>0 and frame.height>0
            has_caption=any(s['start']<c['end'] and s['end']>c['start'] for s in p['transcript'])
            if c['style']!='none' and has_caption or c.get('overlay_text'):
                ass=path.parent/f"{c['id']}-{path.stem}.ass"
                assert ass.exists() and 'Dialogue:' in ass.read_text(encoding='utf-8'),'Expected timed captions were not found'
            results.append({'project_id':p['id'],'clip_id':c['id'],'status':'passed',**info})
        except Exception as exc:
            results.append({'project_id':p['id'],'clip_id':c['id'],'status':'failed','error':str(exc)})
failed=[r for r in results if r['status']=='failed']
report={'status':'passed' if not failed else 'failed','verified_ready_exports':len(results),'failed_exports':len(failed),'historical_project_errors':history,'exports':results}
Path('artifacts').mkdir(exist_ok=True)
Path('artifacts/saved-export-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'status':report['status'],'verified_ready_exports':len(results),'failed_exports':len(failed),'historical_project_errors':history},indent=2))
raise SystemExit(1 if failed else 0)
