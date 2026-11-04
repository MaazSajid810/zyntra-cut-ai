import json
import time

import pytest
from fastapi.testclient import TestClient
from backend import guest,main,media,store


@pytest.fixture
def workspace(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DATA',tmp_path)
    with TestClient(main.app) as a:
        b=TestClient(main.app)
        a.get('/api/session');b.get('/api/session')
        source=tmp_path/'fixture.mp4'
        media.run(['-f','lavfi','-i','color=c=green:s=160x90:r=15','-t','1','-c:v','libx264',str(source)])
        with source.open('rb') as f:
            uploaded=a.post('/api/projects',files={'file':('private.mp4',f,'video/mp4')})
        assert uploaded.status_code==201,uploaded.text
        p=uploaded.json()
        p=a.post(f"/api/projects/{p['id']}/clips",json={'title':'Private clip','start':0,'end':.8,'style':'none'}).json()
        yield a,b,p
        b.close()


def test_session_cookie_and_hash_storage(workspace,monkeypatch):
    a,b,p=workspace
    response=a.get('/api/session')
    cookie=response.headers['set-cookie'].lower()
    assert 'httponly' in cookie and 'samesite=strict' in cookie and 'path=/' in cookie
    assert a.cookies.get(guest.COOKIE)!=b.cookies.get(guest.COOKIE)
    assert a.get('/api/projects').json()[0]['id']==p['id']
    assert b.get('/api/projects').json()==[]
    assert b.get(f"/api/projects/{p['id']}",headers={'X-Owner-Id':p['owner_id']}).status_code==404
    token=a.cookies.get(guest.COOKIE)
    with store.connect() as db:
        rows=list(db.execute('SELECT token_hash FROM guest_sessions'))
    assert token not in str(rows)
    assert guest.digest(token) in str(rows)
    monkeypatch.setenv('CLIPFORGE_COOKIE_SECURE','true')
    assert 'secure' in a.get('/api/session').headers['set-cookie'].lower()


@pytest.mark.parametrize('suffix',['','/media/source','/media/poster','/subtitles?format=srt','/subtitles?format=vtt'])
def test_other_guest_cannot_read_private_project(workspace,suffix):
    a,b,p=workspace
    path=f"/api/projects/{p['id']}"+suffix
    assert b.get(path,headers={'Range':'bytes=0-99'}).status_code==404
    assert a.get(path).status_code==200
    assert 'no-store' in a.get(path).headers['cache-control']


@pytest.mark.parametrize('method,suffix,body',[
    ('POST','/transcribe',{}),('POST','/highlights',{'clip_count':1}),
    ('PUT','/transcript',[]),('POST','/clips',{'title':'Stolen','start':0,'end':.5}),
    ('PUT','/clips/CLIP',{'title':'Stolen','start':0,'end':.5}),
    ('POST','/clips/CLIP/render',None),('POST','/clips/render',None),
    ('PUT','/clips/settings',{}),('DELETE','/clips/CLIP',None),('DELETE','',None),
])
def test_other_guest_cannot_change_or_delete_project(workspace,method,suffix,body):
    a,b,p=workspace
    path=f"/api/projects/{p['id']}"+suffix.replace('CLIP',p['clips'][0]['id'])
    before=store.get(p['id'])
    response=b.request(method,path,json=body)
    assert response.status_code==404,response.text
    assert store.get(p['id'])==before


def test_missing_tampered_expired_cookie_and_csrf(workspace):
    a,b,p=workspace
    outsider=TestClient(main.app)
    assert outsider.get('/api/projects').status_code==401
    outsider.cookies.set(guest.COOKIE,'not-a-valid-session')
    assert outsider.get(f"/api/projects/{p['id']}/media/source").status_code==401
    assert outsider.get('/api/session').status_code==200
    assert outsider.get('/api/projects').json()==[]
    with store.connect() as db:
        db.execute('UPDATE guest_sessions SET expires_at=0 WHERE token_hash=?',(guest.digest(a.cookies.get(guest.COOKIE)),))
    assert a.get('/api/projects').status_code==401
    a.get('/api/session')
    assert a.get('/api/projects').json()==[]
    assert b.post('/api/projects',headers={'Origin':'https://evil.example'}).status_code==403
    assert b.get('/api/session',headers={'Sec-Fetch-Site':'cross-site'}).status_code==403
    outsider.close()


def test_import_job_is_private(workspace,monkeypatch):
    a,b,p=workspace
    monkeypatch.setattr(main.importer,'validate_public_url',lambda url:url)
    monkeypatch.setattr(main.import_pool,'submit',lambda *args:None)
    job=a.post('/api/imports',json={'url':'https://example.com/video.mp4'}).json()
    assert a.get('/api/imports/'+job['id']).status_code==200
    assert b.get('/api/imports/'+job['id']).status_code==404
    assert store.import_get(job['id'])['owner_id']==p['owner_id']


def test_owner_can_delete_clip_and_all_revisions_without_source_loss(workspace):
    a,b,p=workspace
    pid=p['id'];cid=p['clips'][0]['id'];folder=store.DATA/pid
    assert a.post(f'/api/projects/{pid}/clips/{cid}/render').status_code==202
    deadline=time.monotonic()+20
    while time.monotonic()<deadline:
        p=a.get('/api/projects/'+pid).json()
        if p['clips'][0]['status'] in ('ready','error'):break
        time.sleep(.05)
    assert p['clips'][0]['status']=='ready',p
    assert a.get(f'/api/projects/{pid}/media/{cid}',headers={'Range':'bytes=0-99'}).status_code==206
    assert b.get(f'/api/projects/{pid}/media/{cid}').status_code==404
    # Keep an earlier revision and ASS file to exercise actual disk cleanup.
    (folder/f'{cid}-old.mp4').write_bytes(b'old output')
    (folder/f'{cid}-old.ass').write_text('old captions')
    other=a.post(f'/api/projects/{pid}/clips',json={'title':'Keep','start':0,'end':.5}).json()['clips'][-1]
    assert a.delete(f'/api/projects/{pid}/clips/{cid}').status_code==204
    assert not list(folder.glob(cid+'-*'))
    assert (folder/'source').is_file()
    assert [c['id'] for c in a.get('/api/projects/'+pid).json()['clips']]==[other['id']]
    assert a.get(f'/api/projects/{pid}/media/{cid}').status_code==404
    assert a.delete(f'/api/projects/{pid}/clips/{cid}').status_code==404
    store.import_save({'id':'linked-job','owner_id':p['owner_id'],'project_id':pid,'status':'ready'})
    assert a.delete('/api/projects/'+pid).status_code==204
    assert not folder.exists() and store.get(pid) is None and store.import_get('linked-job') is None


def test_busy_project_cannot_be_deleted(workspace):
    a,b,p=workspace
    store.mutate(p['id'],lambda item:item['clips'][0].update(status='rendering'))
    assert a.delete(f"/api/projects/{p['id']}/clips/{p['clips'][0]['id']}").status_code==409
    assert a.delete(f"/api/projects/{p['id']}").status_code==409


def test_legacy_data_requires_one_time_local_key(workspace):
    a,b,p=workspace
    store.save({'id':'legacy-project','status':'uploaded','clips':[]})
    guest.prepare_legacy()
    keyfile=store.DATA/'legacy-workspace-key.txt'
    key=keyfile.read_text()
    assert a.get('/api/projects/legacy-project').status_code==404
    assert b.get('/api/projects/legacy-project').status_code==404
    assert b.post('/api/session/claim-legacy',json={'key':'x'*43}).status_code==400
    claimed=a.post('/api/session/claim-legacy',json={'key':key})
    assert claimed.status_code==200 and claimed.json()['projects']==1
    assert a.get('/api/projects/legacy-project').status_code==200
    assert b.get('/api/projects/legacy-project').status_code==404
    assert b.post('/api/session/claim-legacy',json={'key':key}).status_code==400
    assert not keyfile.exists()
    with store.connect() as db:
        assert not db.execute("SELECT 1 FROM settings WHERE key='legacy_claim_hash'").fetchone()
