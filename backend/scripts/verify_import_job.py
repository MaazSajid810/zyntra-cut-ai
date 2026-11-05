"""Validate actual imported clip files without modifying the user's project."""
import argparse
import json
from pathlib import Path

import av
from backend import media,store

parser=argparse.ArgumentParser()
parser.add_argument('job_id')
args=parser.parse_args()
job=store.import_get(args.job_id)
assert job and job['status']=='ready',job
p=store.get(job['project_id'])
assert p and p['status']=='ready' and p['transcript'] and p['clips'],p
verified=[]
for clip in p['clips']:
    assert clip['status']=='ready',clip
    path=store.DATA/p['id']/clip['file']
    info=media.probe(path)
    assert info['duration']>0 and abs(info['duration']-(clip['end']-clip['start']))<.5
    assert info['has_audio']==(p['has_audio'] and clip.get('voice_effect')!='mute')
    with av.open(str(path)) as container:
        frame=next(container.decode(video=0))
        assert frame.width>0 and frame.height>0
    verified.append({'id':clip['id'],'status':'passed','style':clip['style'],'bytes':path.stat().st_size,**info})
report={'status':'passed','source_url':p.get('source_url'),'name':p['name'],'duration':p['duration'],'transcript_segments':len(p['transcript']),'requested_clips':p.get('requested_clip_count'),'verified_clips':verified}
Path('artifacts').mkdir(exist_ok=True)
Path('artifacts/verified-link-import.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
