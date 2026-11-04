"""Real speech through the API job queue, Whisper, highlights and MP4 export.

Run verify_whisper first to cache the public fixture and base model.
All project data is temporary; the verified MP4 is copied to artifacts/.
"""
import json
import os
import shutil
import tempfile
import time
from pathlib import Path

from fastapi.testclient import TestClient
from faster_whisper import WhisperModel

from backend import main, media, store

cache = store.DATA
assert (cache / 'jfk.flac').is_file(), 'Run python -m scripts.verify_whisper first.'
mode=os.environ.get('CLIPFORGE_TEST_MODE','balanced')
automatic=os.environ.get('CLIPFORGE_TEST_AUTOPREVIEW')=='1'
if mode!='fast':
    main.model = WhisperModel('base', device='cpu', compute_type='int8', download_root=str(cache / 'models'), local_files_only=True)
else:
    main.models['tiny'] = WhisperModel('tiny', device='cpu', compute_type='int8', download_root=str(cache / 'models'))
artifacts = Path('artifacts').resolve()
artifacts.mkdir(exist_ok=True)

def wait(client, pid, predicate):
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        p = client.get(f'/api/projects/{pid}').json()
        assert p['status'] != 'error', p['error']
        if predicate(p):
            return p
        time.sleep(.2)
    raise TimeoutError('Real speech processing did not finish in three minutes')

with tempfile.TemporaryDirectory(prefix='clipforge-speech-') as tmp:
    store.DATA = Path(tmp)
    source = store.DATA / 'speech.mp4'
    media.run(['-f','lavfi','-i','color=c=0x1e3027:s=640x360:r=24','-i',str(cache/'jfk.flac'),'-shortest','-c:v','libx264','-c:a','aac',str(source)])
    with TestClient(main.app) as client:
        assert client.get('/api/session').status_code == 200
        with source.open('rb') as file:
            response = client.post('/api/projects', files={'file':('speech.mp4',file,'video/mp4')})
        assert response.status_code == 201, response.text
        pid = response.json()['id']
        assert client.post(f'/api/projects/{pid}/transcribe', json={'clip_count':30,'transcription_mode':mode,'selection_mode':'all','auto_render':automatic,'generated_settings':{'render_quality':'fast','aspect':'original'}}).status_code == 202
        p = wait(client,pid,lambda p:p['status']=='ready')
        assert 'country' in ' '.join(s['text'] for s in p['transcript']).lower()
        assert all(s.get('words') for s in p['transcript']), 'Real speech must return aligned words'
        assert p['clips'], p
        assert p['requested_clip_count'] == 30
        assert p['clip_generation']['requested'] == 30
        assert p['clip_generation']['created'] == len(p['clips']) == 1
        cid = p['clips'][0]['id']
        if not automatic:assert client.post(f'/api/projects/{pid}/clips/{cid}/render').status_code == 202
        p = wait(client,pid,lambda p:p['clips'][0]['status'] in ('ready','error'))
        clip = p['clips'][0]
        assert clip['status']=='ready', clip
        ass=next((store.DATA/pid).glob('*.ass')).read_text(encoding='utf-8')
        assert ass.count('Dialogue: 0,')>10 and r'\1c' in ass
        assert not clip['sticker_enabled'] and 'FOLLOW' not in ass
        shutil.copyfile(store.DATA/pid/clip['file'],artifacts/'verified-speech-clip.mp4')
        if automatic:
            original_ranges=[(c['id'],c['start'],c['end']) for c in p['clips']]
            assert client.post(f'/api/projects/{pid}/transcribe',json={'redo':True,'auto_render':True,'transcription_mode':mode}).status_code==202
            p=wait(client,pid,lambda p:p['status']=='ready')
            assert [(c['id'],c['start'],c['end']) for c in p['clips']]==original_ranges
            assert all(c['status']=='draft' and c['file'] is None for c in p['clips'])
            assert all(s.get('words') for s in p['transcript'])
        assert client.delete(f'/api/projects/{pid}').status_code == 204
        assert client.get(f'/api/projects/{pid}').status_code == 404
        print(json.dumps({'status':'passed','automatic_preview':automatic,'retranscription_preserves_ranges':automatic,'transcription_mode':mode,'transcript':p['transcript'],'highlight':clip,'export':'artifacts/verified-speech-clip.mp4'},indent=2))
