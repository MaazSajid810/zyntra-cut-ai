import io
import time
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend import main,platform,store,guest,media


@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DATA',tmp_path)
    with TestClient(main.app) as client:
        client.get('/api/session');yield client


def wait_job(client):
    for _ in range(120):
        jobs=client.get('/api/studio').json()
        if jobs and jobs[0]['status'] not in ('queued','rendering'):return jobs[0]
        time.sleep(.1)
    pytest.fail('Studio did not finish a short real render')


@pytest.mark.parametrize('text,operation,changes',[
    ('generate 7 clips, 15-30 seconds','generate',{'clip_count':7,'min_duration':15,'max_duration':30}),
    ('captions yellow','edit',{'style':'yellow'}),('trim 2-15','edit',{'start':2,'end':15}),
    ('vertical','edit',{'aspect':'vertical'}),('font size 72','edit',{'subtitle_size':72}),
    ('speed 1.2x','edit',{'speed':1.2}),('voice deep','edit',{'voice_effect':'deep'}),('render','render',{})])
def test_local_command_plan_is_concrete(text,operation,changes):
    plan=platform.parse_command(text,'a'*32,'b'*32)
    assert plan['operation']==operation
    assert changes.items()<=plan['body'].items()


@pytest.mark.parametrize('text',['generate 101 clips','generate 2 clips, 50-10 seconds','speed 9x','trim 12-3','make a photorealistic fox video'])
def test_unsupported_commands_are_not_fabricated(text):
    with pytest.raises(ValueError):platform.parse_command(text,'a'*32,'b'*32)


def test_wizard_ownership_and_history(client):
    pid='a'*32;owner=guest.owner_for_token(client.cookies.get(guest.COOKIE))
    store.save({'id':pid,'owner_id':owner,'clips':[{'id':'b'*32,'status':'draft'}],'status':'ready'})
    assert client.post('/api/wizard/plan',json={'project_id':pid,'clip_id':'b'*32,'message':'vertical'}).status_code==200
    history={'messages':[{'role':'user','text':'My private edit'}]}
    assert client.put('/api/wizard/history',json=history).status_code==200
    with TestClient(main.app) as other:
        other.get('/api/session')
        assert other.get('/api/wizard/history').json()=={'messages':[]}
        assert other.post('/api/wizard/plan',json={'project_id':pid,'message':'generate 2 clips'}).status_code==404
    assert client.get('/api/wizard/history').json()==history
    assert client.delete('/api/wizard/history').status_code==204
    assert client.get('/api/wizard/history').json()=={'messages':[]}


def test_discovery_uses_actual_observations_and_stale_errors(client,monkeypatch):
    now=[10000];calls=[]
    monkeypatch.setattr(platform,'time',SimpleNamespace(time=lambda:now[0]))
    def search(query):
        calls.append(query)
        return [{'id':'abcdefghijk','title':'Real upstream fixture','views':100 if len(calls)==1 else 130,'views_per_hour':None}]
    monkeypatch.setattr(platform,'public_search',search)
    first=client.get('/api/discover').json()
    assert first['items'][0]['views_per_hour'] is None
    assert client.get('/api/discover?refresh=true').json()==first and len(calls)==1
    now[0]+=600
    second=client.get('/api/discover?refresh=true').json()
    assert second['items'][0]['views_per_hour']==180
    assert 'not a verified trending chart' in second['message']
    assert client.get('/api/discover?category=made-up').status_code==422
    now[0]+=600
    monkeypatch.setattr(platform,'public_search',lambda _:(_ for _ in ()).throw(RuntimeError('upstream unavailable')))
    assert client.get('/api/discover?refresh=true').json()['stale']
    assert client.get('/api/discover?category=Tech').status_code==502


def test_actual_studio_png_private_and_delete(client):
    image=Image.new('RGB',(200,300),'red');photo=io.BytesIO();image.save(photo,format='PNG')
    result=client.post('/api/studio',data={'text':'A real local design','kind':'image','quality':'480'},files={'file':('photo.png',photo.getvalue(),'image/png')})
    assert result.status_code==202,result.text
    job=wait_job(client);assert job['status']=='ready',job
    response=client.get('/api/studio/'+job['id']+'/media');assert response.status_code==200
    with Image.open(io.BytesIO(response.content)) as output:assert output.width==480 and output.height>800
    with TestClient(main.app) as other:
        other.get('/api/session');assert other.get('/api/studio').json()==[]
        assert other.get('/api/studio/'+job['id']+'/media').status_code==404
        assert other.delete('/api/studio/'+job['id']).status_code==404
    assert client.delete('/api/studio/'+job['id']).status_code==204
    assert not (store.DATA/job['id']).exists()


def test_actual_studio_video_and_project_are_editable(client,tmp_path):
    r=client.post('/api/studio',data={'text':'Real motion. Real export.','kind':'video','duration':'3','quality':'480'})
    assert r.status_code==202,r.text
    job=wait_job(client);assert job['status']=='ready',job
    output=client.get('/api/studio/'+job['id']+'/media');assert output.status_code==200
    path=tmp_path/'result.mp4';path.write_bytes(output.content);info=media.probe(path)
    assert abs(info['duration']-3)<.1 and info['width']==480
    p=client.get('/api/projects/'+job['project_id']);assert p.status_code==200
    assert not p.json()['has_audio']
    assert client.post('/api/projects/'+job['project_id']+'/clips',json={'title':'Studio edit','start':0,'end':2}).status_code==201
    assert client.delete('/api/studio/'+job['id']).status_code==204
    assert client.get('/api/projects/'+job['project_id']).status_code==404


def test_studio_rejects_bad_inputs_without_abandoned_jobs(client):
    assert client.post('/api/studio',data={'text':'','kind':'video'}).status_code==422
    assert client.post('/api/studio',data={'text':'Test','duration':'1'}).status_code==422
    assert client.post('/api/studio',data={'text':'Test'},files={'file':('bad.png',b'not an image','image/png')}).status_code==400
    assert client.get('/api/studio').json()==[]


def test_studio_admission_and_interrupted_job_recovery(client):
    owner=guest.owner_for_token(client.cookies.get(guest.COOKIE))
    job={'id':'a'*32,'owner_id':owner,'status':'queued','options':{},'error':None}
    platform.claim_studio(job)
    r=client.post('/api/studio',data={'text':'Must wait','kind':'image'})
    assert r.status_code==409
    assert not any(p.name!='clipforge.db' for p in store.DATA.iterdir())
    platform.recover_studio()
    assert 'interrupted' in client.get('/api/studio').json()[0]['error']
    assert client.get('/api/studio').json()[0]['status']=='error'


def test_wizard_import_preserves_custom_quantity_duration():
    p=platform.parse_command('make 9 clips, 20-40 seconds https://www.youtube.com/watch?v=abcdefghijk')
    assert p['operation']=='import'
    assert p['body']['clip_count']==9 and p['body']['min_duration']==20 and p['body']['max_duration']==40
