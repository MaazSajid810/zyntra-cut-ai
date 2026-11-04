import time
import av
import numpy as np

import pytest
from fastapi.testclient import TestClient

from backend import main, media, store, guest


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(store, 'DATA', tmp_path)
    with TestClient(main.app) as client:
        client.get('/api/session')
        yield client


def test_real_upload_edit_render_and_range_download(client, tmp_path):
    video = tmp_path / 'fixture.mp4'
    media.run(['-f', 'lavfi', '-i', 'testsrc2=size=320x180:rate=15', '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=16000', '-t', '3', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', str(video)])
    with video.open('rb') as file:
        response = client.post('/api/projects', files={'file': ('example.mp4', file, 'video/mp4')})
    assert response.status_code == 201, response.text
    project = response.json()
    pid = project['id']
    assert project['duration'] == pytest.approx(3, abs=.2)
    assert client.get(f'/api/projects/{pid}/media/poster').status_code == 200
    assert client.get(f'/api/projects/{pid}/media/source', headers={'Range': 'bytes=0-99'}).status_code == 206
    subtitles = [{'id': 0, 'start': 0, 'end': 2, 'text': 'Real export test {literal} \\ text'}]
    assert client.put(f'/api/projects/{pid}/transcript', json=subtitles).status_code == 200
    body = {'title': 'Real test clip', 'start': 0, 'end': 2, 'aspect': 'vertical', 'style': 'mint', 'render_quality':'standard'}
    assert client.post(f'/api/projects/{pid}/clips', json={**body, 'end': 8}).status_code == 400
    created = client.post(f'/api/projects/{pid}/clips', json=body)
    assert created.status_code == 201
    clip = created.json()['clips'][0]
    cid = clip['id']
    assert client.post(f'/api/projects/{pid}/clips', json={**body, 'title':'Second batch clip', 'start':2, 'end':3}).status_code == 201
    assert client.post(f'/api/projects/{pid}/clips/render').status_code == 202
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        clips = client.get(f'/api/projects/{pid}').json()['clips']
        clip = clips[0]
        if all(c['status'] not in ('queued', 'rendering') for c in clips):
            break
        time.sleep(.1)
    assert clip['status'] == 'ready', clip
    assert all(c['status'] == 'ready' for c in clips), clips
    assert client.post(f'/api/projects/{pid}/clips/render').status_code == 400
    output = store.DATA / pid / clip['file']
    info = media.probe(output)
    assert (info['width'], info['height']) == (720, 1280)
    assert info['duration'] == pytest.approx(2, abs=.2)
    assert info['has_audio']
    exported = client.get(f'/api/projects/{pid}/media/{cid}')
    assert exported.status_code == 200
    assert exported.headers['content-type'] == 'video/mp4'
    assert len(exported.content) > 1000
    # Editing text invalidates the old render instead of serving stale subtitles.
    assert client.put(f'/api/projects/{pid}/transcript', json=[{**subtitles[0], 'text': 'Changed'}]).status_code == 200
    assert client.get(f'/api/projects/{pid}/media/{cid}').status_code == 404
    assert client.delete(f'/api/projects/{pid}').status_code == 204
    assert client.get(f'/api/projects/{pid}').status_code == 404
    assert not (store.DATA / pid).exists()


def test_invalid_upload_and_access_controls(client):
    response = client.post('/api/projects', files={'file': ('fake.mp4', b'not a video', 'video/mp4')})
    assert response.status_code == 400
    assert client.get('/api/projects').json() == []
    assert client.get('/api/projects/does-not-exist').status_code == 404
    assert client.post('/api/projects', headers={'Origin':'https://untrusted.example'}).status_code == 403
    assert client.get('/api/projects/..%2F..%2F/media/source').status_code == 404

def test_warm_vintage_save_render_and_versioned_download(client,tmp_path):
    source=tmp_path/'gray.mp4'
    media.run(['-f','lavfi','-i','color=c=gray:s=320x180:r=15','-t','1','-c:v','libx264',str(source)])
    with source.open('rb') as f:
        p=client.post('/api/projects',files={'file':('gray.mp4',f,'video/mp4')}).json()
    pid=p['id']
    options={'title':'Filter regression','start':0,'end':.8,'style':'none','aspect':'original'}
    c=client.post(f'/api/projects/{pid}/clips',json=options).json()['clips'][0]
    cid=c['id'];versions=[];frames={}
    for effect in ['none','warm','vintage']:
        assert client.put(f'/api/projects/{pid}/clips/{cid}',json={**options,'video_effect':effect}).status_code==200
        assert client.post(f'/api/projects/{pid}/clips/{cid}/render').status_code==202
        deadline=time.monotonic()+20
        while time.monotonic()<deadline:
            c=client.get(f'/api/projects/{pid}').json()['clips'][0]
            if c['status'] in ('ready','error'):break
            time.sleep(.05)
        assert c['status']=='ready',c
        assert c['video_effect']==effect
        versions.append(c['file'])
        response=client.get(f"/api/projects/{pid}/media/{cid}?v={c['file']}")
        assert response.status_code==200 and 'no-store' in response.headers['cache-control']
        output=tmp_path/f'{effect}.mp4';output.write_bytes(response.content)
        with av.open(str(output)) as video:
            frames[effect]=next(video.decode(video=0)).to_ndarray(format='rgb24').astype(float)
    assert len(set(versions))==3
    # Warm actually shifts neutral footage toward red; vintage darkens corners.
    assert frames['warm'][:,:,0].mean()-frames['warm'][:,:,2].mean()>15
    assert np.abs(frames['vintage']-frames['none']).mean()>5
    assert frames['vintage'][:20,:20].mean()<frames['vintage'][70:110,120:200].mean()-5


def test_highlights_are_grounded_and_do_not_overlap():
    segments = [{'start': i*5, 'end': (i+1)*5, 'text': 'Why did we learn this surprising secret?'} for i in range(30)]
    clips = media.highlights(segments, 150)
    assert 1 <= len(clips) <= 5
    assert all(0 <= c['start'] < c['end'] <= 150 for c in clips)
    assert all(c['title'] in ' '.join(s['text'] for s in segments) for c in clips)
    assert media.highlights([], 150) == []
    for a, b in zip(clips, clips[1:]):
        assert a['end'] <= b['start']


@pytest.mark.parametrize('count', [7, 12, 30, 100])
def test_requested_count_and_existing_clips_are_preserved(client, count):
    transcript = [{'id': i, 'start': i*5, 'end': (i+1)*5, 'text': f'Why did we learn this surprising secret number {i}?'} for i in range(1500)]
    manual = {'id':'keep-me', 'start':0, 'end':5, 'status':'ready', 'title':'Keep my export', 'file':'saved.mp4'}
    store.save({'id':'count-test', 'owner_id':guest.owner_for_token(client.cookies.get(guest.COOKIE)), 'duration':7500, 'status':'ready', 'transcript':transcript, 'clips':[manual]})
    response = client.post('/api/projects/count-test/highlights', json={'selection_mode':'all','clip_count':count})
    assert response.status_code == 200, response.text
    p = response.json()
    assert p['requested_clip_count'] == count
    assert p['clip_generation']['created'] == count
    assert len(p['clips']) == count + 1
    assert p['clips'][0] == manual
    assert all(c['start'] >= 5 for c in p['clips'][1:])
    before = {c['id'] for c in p['clips']}
    response = client.post('/api/projects/count-test/highlights', json={'selection_mode':'all','clip_count':5})
    clips = response.json()['clips']
    assert before.issubset({c['id'] for c in clips})
    assert len(clips) == count + 6
    chronological = sorted(clips, key=lambda c:c['start'])
    assert all(a['end'] <= b['start'] for a,b in zip(chronological,chronological[1:]))


def test_short_video_reports_actual_count_and_count_validation(client):
    store.save({'id':'short-test', 'owner_id':guest.owner_for_token(client.cookies.get(guest.COOKIE)), 'duration':11, 'status':'ready', 'transcript':[{'id':0,'start':0,'end':11,'text':'This short video has only one complete speech highlight.'}], 'clips':[]})
    for value in [0, -1, 101, 1.5, '30', True]:
        for endpoint in ['highlights','transcribe']:
            assert client.post(f'/api/projects/short-test/{endpoint}', json={'selection_mode':'all','clip_count':value}).status_code == 422
    p = client.post('/api/projects/short-test/highlights', json={'selection_mode':'all','clip_count':100}).json()
    assert p['clip_generation']['requested'] == 100
    assert p['clip_generation']['created'] == 1
    assert '1 of 100' in p['clip_generation']['message']
    assert len(p['clips']) == 1
    p = client.post('/api/projects/short-test/highlights', json={'selection_mode':'all','clip_count':30}).json()
    assert p['clip_generation']['created'] == 0
    assert len(p['clips']) == 1
    p['status'] = 'transcribing'
    store.save(p)
    assert client.post('/api/projects/short-test/highlights', json={'selection_mode':'all','clip_count':5}).status_code == 409
    assert client.post('/api/projects/short-test/clips/render').status_code == 409


def test_bulk_effect_settings_and_subtitle_downloads(client):
    segment={'id':0,'start':5,'end':12,'text':'My editable subtitle'}
    drafts=[{'id':str(i),'title':f'Distinct clip {i}','start':6+i,'end':11+i,'status':status,'file':None,**main.EffectSettings().model_dump()} for i,status in enumerate(['draft','error','ready'])]
    drafts[2]['file']='kept.mp4'
    store.save({'id':'style-test','owner_id':guest.owner_for_token(client.cookies.get(guest.COOKIE)),'duration':20,'status':'ready','transcript':[segment],'clips':drafts})
    options=main.EffectSettings(voice_effect='deep',video_effect='vintage',style='boxed',aspect='portrait',output_format='webm',overlay_text='My custom hook').model_dump()
    response=client.put('/api/projects/style-test/clips/settings',json=options)
    assert response.status_code==200,response.text
    result=response.json()['clips']
    for c in result[:2]:
        assert all(c[key]==value for key,value in options.items())
        assert c['status']=='draft'
    assert result[2]==drafts[2]
    updated=client.put('/api/projects/style-test/clips/settings?include_ready=true',json={**options,'sticker':'subscribe','aspect':'vertical'}).json()['clips']
    assert [tuple(c[key] for key in ('id','title','start','end')) for c in updated]==[tuple(c[key] for key in ('id','title','start','end')) for c in drafts]
    assert all(c['aspect']=='vertical' for c in updated)
    assert store.get('style-test')['transcript']==[segment]
    assert all(c['overlay_text']=='My custom hook' and c['sticker']=='subscribe' and c['status']=='draft' and c['file'] is None for c in updated)
    assert client.put('/api/projects/style-test/clips/settings',json={**options,'subtitle_color':'invalid'}).status_code==422
    srt=client.get('/api/projects/style-test/subtitles?format=srt&clip_id=0')
    assert srt.status_code==200
    assert '00:00:00,000 --> 00:00:05,000' in srt.text
    assert 'My editable subtitle' in srt.text
    assert 'attachment' in srt.headers['content-disposition']
    vtt=client.get('/api/projects/style-test/subtitles?format=vtt')
    assert vtt.text.startswith('WEBVTT')
    assert client.get('/api/projects/style-test/subtitles?format=wrong').status_code==422
    assert client.get('/api/projects/style-test/subtitles?clip_id=missing').status_code==404
