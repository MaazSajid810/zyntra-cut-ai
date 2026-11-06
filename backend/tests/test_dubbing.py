"""Real local voice synthesis, sentence timing, export audio and guest isolation."""
import time
import wave
from copy import deepcopy
from pathlib import Path

import av
import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend import dubbing,guest,main,media,store,translation


@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DATA',tmp_path)
    with TestClient(main.app) as client:
        client.get('/api/session')
        yield client


def wait(client,pid):
    deadline=time.monotonic()+60
    while time.monotonic()<deadline:
        p=client.get('/api/projects/'+pid).json()
        if p['status'] not in ('queued','transcribing','analyzing'):
            return p
        time.sleep(.05)
    pytest.fail('Dubbing did not finish')


def audio(path):
    with av.open(str(path)) as container:
        resampler=av.AudioResampler(format='s16',layout='mono',rate=22050)
        frames=[out.to_ndarray().reshape(-1) for frame in container.decode(audio=0) for out in resampler.resample(frame)]
        return np.concatenate(frames)


def project(client,tmp_path):
    path=tmp_path/'fixture.mp4'
    media.run(['-f','lavfi','-i','testsrc2=size=320x180:rate=15','-f','lavfi','-i','sine=frequency=440:sample_rate=22050','-t','8','-c:v','libx264','-c:a','aac',str(path)])
    p=client.post('/api/projects',files={'file':('Dubbing fixture.mp4',path.read_bytes(),'video/mp4')}).json()
    source=[{'id':0,'start':1,'end':6,'text':'Hello. Welcome to my channel.'}]
    store.mutate(p['id'],lambda p:p.update(language='en',transcript=deepcopy(source),source_transcript=deepcopy(source),status='ready'))
    client.post('/api/projects/'+p['id']+'/clips',json={'start':0,'end':8,'title':'Translated voice','style':'clean','render_quality':'fast','sound_effect':'ding','sound_at':7})
    return p['id'],source


@pytest.mark.parametrize('script,language',[('urdu','ur'),('hindi','hi'),('spanish','es')])
def test_real_translation_voice_and_mp4_do_not_reuse_original_audio(client,tmp_path,script,language):
    if not dubbing.executable() or not translation.route_available('en',language):
        pytest.skip('Run the documented local translation and dubbing setup')
    pid,source=project(client,tmp_path);base='/api/projects/'+pid
    r=client.post(base+'/dubbing',json={'caption_script':script})
    assert r.status_code==202,r.text
    p=wait(client,pid)
    assert not p.get('dubbing_error'),p
    assert p['source_transcript']==source and p['language']=='en'
    assert p['transcript'][0]['text']!=source[0]['text']
    assert p['transcript'][0]['start']==1 and p['transcript'][0]['end']==6
    assert p['transcript'][0]['timing']=='dubbed_sentence' and 'words' not in p['transcript'][0]
    assert p['dubbing']['enabled'] and p['dubbing']['language']==language and p['dubbing']['mouth_animation'] is False
    data=audio(store.DATA/pid/p['dubbing']['file'])
    assert len(data)/22050==pytest.approx(8,abs=.01)
    assert np.max(np.abs(data[:int(.95*22050)]))==0
    assert np.max(np.abs(data[int(1.1*22050):int(5.8*22050)]))>100
    assert np.max(np.abs(data[int(6.1*22050):]))==0
    assert client.get(base+'/dubbing/audio',headers={'Range':'bytes=0-99'}).status_code==206
    preview=store.DATA/pid/p['dubbing']['video_file']
    assert media.probe(preview)['duration']==pytest.approx(8,abs=.15)
    preview_audio=audio(preview)
    assert np.max(np.abs(preview_audio[:int(.9*22050)]))<20
    assert np.max(np.abs(preview_audio[int(1.1*22050):int(5.8*22050)]))>100
    assert client.get(base+'/dubbing/video',headers={'Range':'bytes=0-99'}).status_code==206
    cid=p['clips'][0]['id']
    main.render_clip(pid,cid)
    c=client.get(base).json()['clips'][0]
    assert c['status']=='ready',c
    result=store.DATA/pid/c['file']
    assert media.probe(result)['duration']==pytest.approx(8,abs=.15)
    samples=audio(result)
    # Source was a continuous tone. The exported dubbed voice keeps pre-speech silence,
    # with an independent sound effect at 7s proving compositor input indexing works.
    assert np.max(np.abs(samples[:int(.9*22050)]))<20
    assert np.max(np.abs(samples[int(1.1*22050):int(5.8*22050)]))>100
    assert np.max(np.abs(samples[int(7.05*22050):]))>100
    with TestClient(main.app) as other:
        other.get('/api/session')
        assert other.get(base+'/dubbing/audio').status_code==404
        assert other.get(base+'/dubbing/video').status_code==404
        assert other.post(base+'/dubbing',json={'caption_script':'english'}).status_code==404
    assert client.post(base+'/dubbing',json={'enabled':False}).status_code==202
    assert client.get(base+'/dubbing/audio').status_code==404
    assert client.get(base+'/dubbing/video').status_code==404
    assert client.get(base).json()['clips'][0]['status']=='draft'


def test_dubbed_voice_cannot_render_after_transcript_edits(client,tmp_path):
    if not dubbing.executable():pytest.skip('No offline voice engine')
    pid,source=project(client,tmp_path);base='/api/projects/'+pid
    client.post(base+'/dubbing',json={'caption_script':'english'})
    p=wait(client,pid);assert not p.get('dubbing_error')
    client.put(base+'/transcript',json=[{**source[0],'text':'This text has changed.'}])
    r=client.get(base+'/dubbing/audio')
    assert r.status_code==409 and 'out of date' in r.json()['detail']
    assert client.get(base+'/dubbing/video').status_code==409
    cid=p['clips'][0]['id'];main.render_clip(pid,cid)
    assert 'out of date' in client.get(base).json()['clips'][0]['error']


def test_unsupported_route_keeps_captions_clips_and_source(client,tmp_path,monkeypatch):
    monkeypatch.setattr(translation,'ROOT',tmp_path/'uninstalled-models')
    pid,_=project(client,tmp_path);base='/api/projects/'+pid
    before=client.get(base).json()
    r=client.post(base+'/dubbing',json={'caption_script':'pashto'})
    assert r.status_code==400 and 'translation model' in r.json()['detail']
    assert client.get(base).json()==before


def test_overlong_voice_fails_without_truncating_speech_or_leaving_temp_files(tmp_path):
    if not dubbing.executable():pytest.skip('No offline voice engine')
    with pytest.raises(ValueError,match='too long'):
        dubbing.create_track([{'start':0,'end':.1,'text':'This sentence cannot fit in one tenth of a second.'}],'en',1,tmp_path/'track.wav')
    assert not (tmp_path/'track.wav').exists()
    assert not list(tmp_path.glob('zyntra-dub-*'))


def test_saved_hallucination_is_rejected_before_translating_or_speaking(client,tmp_path):
    pid,_=project(client,tmp_path)
    store.mutate(pid,lambda p:p.update(source_transcript=[{'id':0,'start':0,'end':6,'text':'నిని'*60}]))
    before=client.get('/api/projects/'+pid).json()
    response=client.post('/api/projects/'+pid+'/dubbing',json={'caption_script':'urdu'})
    assert response.status_code==400 and 'repeated or unreadable' in response.json()['detail']
    assert client.get('/api/projects/'+pid).json()==before


def test_short_utterance_can_use_adjacent_sentence_without_losing_words(tmp_path):
    if not dubbing.executable():pytest.skip('No offline voice engine')
    segments=[{'id':0,'start':0,'end':.2,'text':'This short time slot cannot fit this sentence.'},
              {'id':1,'start':.2,'end':8,'text':'The next sentence has room.'}]
    dubbing.create_track(segments,'en',8,tmp_path/'merged.wav')
    assert len(segments)==1 and 'time slot' in segments[0]['text'] and 'next sentence' in segments[0]['text']
    assert segments[0]['start']==0 and segments[0]['end']==8


def test_av1_preview_preserves_video_instead_of_transcoding(tmp_path,monkeypatch):
    source=tmp_path/'av1.mp4';track=tmp_path/'voice.wav';output=tmp_path/'dubbed.mp4'
    media.run(['-f','lavfi','-i','color=c=blue:s=160x90:r=5','-t','1','-c:v','libaom-av1','-cpu-used','8','-crf','40',str(source)])
    media.run(['-f','lavfi','-i','sine=frequency=440:sample_rate=22050','-t','1',str(track)])
    calls=[];real_run=media.run
    def record(args,**kwargs):calls.append(args);return real_run(args,**kwargs)
    monkeypatch.setattr(media,'run',record)
    dubbing.create_video(source,track,output,1)
    assert calls[0][calls[0].index('-c:v')+1]=='copy'
    with av.open(str(output)) as container:
        assert container.streams.video[0].codec_context.name in ('av1','libdav1d')
        assert container.streams.audio
