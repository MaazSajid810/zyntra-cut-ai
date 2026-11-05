import threading
import time
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from backend import guest,main,media,store


def test_background_generation_is_responsive_and_renders_ten_actual_mp4s(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DATA',tmp_path)
    source=tmp_path/'batch.mp4'
    media.run(['-f','lavfi','-i','testsrc2=size=320x180:rate=15','-f','lavfi','-i','sine=frequency=440:sample_rate=16000','-t','40','-c:v','libx264','-c:a','aac',str(source)])
    gate=threading.Event();entered=threading.Event()
    def measurements(pid):
        entered.set()
        assert gate.wait(10),'Test did not release the analysis gate'
    monkeypatch.setattr(main,'prepare_analysis',measurements)
    with TestClient(main.app) as client:
        client.get('/api/session')
        pid=client.post('/api/projects',files={'file':('Batch of ten.mp4',source.read_bytes(),'video/mp4')}).json()['id']
        base='/api/projects/'+pid
        segments=[{'id':i,'start':i*4,'end':i*4+3,'text':f'This is distinct source sentence number {i} for the export batch.'} for i in range(10)]
        client.put(base+'/transcript',json=segments)
        response=client.post(base+'/highlights',json={'clip_count':10,'selection_mode':'all','min_duration':3,'max_duration':3,'auto_render':True,'background':True,'generated_settings':{'render_quality':'fast','aspect':'original','style':'clean'}})
        assert response.status_code==202 and response.json()['status']=='analyzing'
        assert entered.wait(2)
        assert client.get('/api/health').status_code==200
        assert client.post(base+'/highlights',json={'clip_count':10}).status_code==409
        gate.set()
        deadline=time.monotonic()+90
        while time.monotonic()<deadline:
            project=client.get(base).json()
            if project['status']=='error' or project['clips'] and (all(c['status']=='ready' for c in project['clips']) or any(c['status']=='error' for c in project['clips'])):break
            time.sleep(.1)
        assert project['clip_generation']['created']==10,project
        assert len(project['clips'])==10 and all(c['status']=='ready' for c in project['clips']),project
        assert len({c['file'] for c in project['clips']})==10
        for c in project['clips']:
            info=media.probe(store.DATA/pid/c['file'])
            assert info['duration']==pytest.approx(3,abs=.15) and info['has_audio']
            assert client.get(base+'/media/'+c['id']).status_code==200


def test_background_failure_is_visible_and_preserves_existing_clips(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DATA',tmp_path)
    def broken(*args):raise RuntimeError('Explicit analysis failure fixture')
    monkeypatch.setattr(main,'prepare_analysis',broken)
    with TestClient(main.app) as client:
        client.get('/api/session')
        clips=[{'id':'kept','status':'ready','file':'kept.mp4'}]
        store.save({'id':'async-failed','owner_id':guest.owner_for_token(client.cookies.get(guest.COOKIE)),'status':'ready',
                    'duration':20,'transcript':[{'id':0,'start':0,'end':10,'text':'Saved source speech.'}],'clips':deepcopy(clips)})
        response=client.post('/api/projects/async-failed/highlights',json={'background':True,'clip_count':10})
        assert response.status_code==202
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            p=client.get('/api/projects/async-failed').json()
            if p['status']=='error':break
            time.sleep(.02)
        assert p['clips']==clips and 'Explicit analysis failure fixture' in p['error']
