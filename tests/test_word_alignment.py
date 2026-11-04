from fastapi.testclient import TestClient
from backend import main,store,guest

def test_edit_preserves_only_unchanged_alignment_and_requires_explicit_redo(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DATA',tmp_path)
    segment={'id':0,'start':0,'end':1,'text':'Real words.','words':[{'start':0,'end':.5,'word':'Real'},{'start':.5,'end':1,'word':'words.'}]}
    with TestClient(main.app) as client:
        client.get('/api/session')
        store.save({'id':'aligned','owner_id':guest.owner_for_token(client.cookies.get(guest.COOKIE)),'status':'ready','has_audio':True,'duration':2,'transcript':[segment],'clips':[]})
        saved=client.put('/api/projects/aligned/transcript',json=[segment])
        assert saved.status_code==200
        assert saved.json()['transcript'][0]['words']==segment['words']
        edited=client.put('/api/projects/aligned/transcript',json=[{**segment,'text':'User edited caption.'}])
        assert edited.status_code==200 and 'words' not in edited.json()['transcript'][0]
        queued=[]
        monkeypatch.setattr(main.pool,'submit',lambda *args:queued.append(args))
        assert client.post('/api/projects/aligned/transcribe',json={}).status_code==409
        redo=client.post('/api/projects/aligned/transcribe',json={'redo':True})
        assert redo.status_code==202 and redo.json()['realign_existing'] and len(queued)==1
