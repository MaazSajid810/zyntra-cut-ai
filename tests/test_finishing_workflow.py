import time
import av
import numpy as np
import pytest
from fastapi.testclient import TestClient
from backend import main,media,store

@pytest.fixture(scope='module')
def video(tmp_path_factory):
    path=tmp_path_factory.mktemp('finishing')/'source.mp4'
    media.run(['-f','lavfi','-i','color=c=black:s=320x180:r=20','-f','lavfi','-i','sine=frequency=440:sample_rate=48000','-t','3','-c:v','libx264','-c:a','aac',str(path)])
    return path

def settings(**changes):return {'id':'test','start':0,'end':3,**main.EffectSettings().model_dump(),'render_quality':'fast','aspect':'square','style':'none',**changes}

@pytest.mark.parametrize('timing,a,b',[('start',0,.4),('middle',.55,.95),('end',1.1,1.5),('custom',.3,.7),('full',0,1.5)])
@pytest.mark.parametrize('animation',['none','pop','fade','slide'])
def test_real_sticker_schedule_and_animation(video,tmp_path,timing,a,b,animation):
    out=tmp_path/'sticker.mp4'
    media.render(video,tmp_path,settings(speed=2,sticker_enabled=True,sticker='subscribe',sticker_timing=timing,sticker_duration=.4,sticker_at=.3,sticker_animation=animation),[],out)
    text=next(tmp_path.glob('*.ass')).read_text(encoding='utf-8')
    assert f'{media.stamp(a)},{media.stamp(b)},Sticker' in text
    with av.open(str(out)) as container:
        samples=[(float(f.pts*f.time_base),f.to_ndarray(format='rgb24')) for f in container.decode(video=0)]
    active=min(samples,key=lambda s:abs(s[0]-(a+b)/2))[1]
    assert (active.max(axis=2)>60).sum()>100
    if timing!='full':
        outside=1.35 if b<1 else .1
        inactive=min(samples,key=lambda s:abs(s[0]-outside))[1]
        assert (inactive.max(axis=2)>60).sum()<20

@pytest.mark.parametrize('voice',['deep','high'])
@pytest.mark.parametrize('strength',[0,.5,1])
def test_rendered_voice_strength_changes_actual_pitch(video,tmp_path,voice,strength):
    from test_effects import audio_frequency
    out=tmp_path/'voice.mp4'
    media.render(video,tmp_path,settings(voice_effect=voice,voice_strength=strength,speed=1.2),[],out)
    ratio=1-.4*strength if voice=='deep' else 1+.5*strength
    assert audio_frequency(out)==pytest.approx(440*ratio,abs=12)
    assert media.probe(out)['duration']==pytest.approx(2.5,abs=.12)

def test_separate_source_subtitle_track_is_not_exported(video,tmp_path):
    srt=tmp_path/'old.srt';srt.write_text('1\n00:00:00,000 --> 00:00:02,000\nOLD SOURCE TRACK\n',encoding='utf-8')
    src=tmp_path/'source.mkv'
    media.run(['-i',str(video),'-i',str(srt),'-map','0','-map','1','-c','copy','-c:s','srt',str(src)])
    with av.open(str(src)) as container:assert len(container.streams.subtitles)==1
    out=tmp_path/'export.mp4'
    media.render(src,tmp_path,settings(style='clean'),[{'start':0,'end':2,'text':'My replacement caption'}],out)
    with av.open(str(out)) as container:assert len(container.streams.subtitles)==0
    ass=next(tmp_path.glob('*.ass')).read_text(encoding='utf-8')
    assert 'OLD SOURCE TRACK' not in ass and 'My replacement caption' in ass

def test_source_caption_cover_blacks_actual_pixels_but_preserves_new_captions(tmp_path):
    source=tmp_path/'burned.mp4'
    media.run(['-f','lavfi','-i','color=c=white:s=320x180:r=20','-t','2','-c:v','libx264',str(source)])
    out=tmp_path/'covered.mp4'
    media.render(source,tmp_path,settings(end=1.5,aspect='original',cover_source_captions=True,style='clean'),[{'start':0,'end':1.5,'text':'NEW WORDS'}],out)
    with av.open(str(out)) as container:pixels=next(container.decode(video=0)).to_ndarray(format='rgb24')
    assert pixels[-10:].mean()<5
    assert pixels[:60].mean()>230
    assert 'NEW WORDS' in next(tmp_path.glob('*.ass')).read_text(encoding='utf-8')

def test_generate_queues_only_new_batch_and_exports_playable_previews(video,tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DATA',tmp_path/'data')
    store.DATA.mkdir()
    with TestClient(main.app) as client:
        client.get('/api/session')
        with video.open('rb') as file:p=client.post('/api/projects',files={'file':('video.mp4',file,'video/mp4')}).json()
        base=f"/api/projects/{p['id']}"
        assert client.put(base+'/transcript',json=[{'id':0,'start':0,'end':2.4,'text':'A complete short fixture.'}]).status_code==200
        old=client.post(base+'/clips',json={'title':'Existing manual clip','start':2.6,'end':3}).json()['clips'][0]
        result=client.post(base+'/highlights',json={'selection_mode':'all','clip_count':5,'auto_render':True,'generated_settings':{'render_quality':'fast','aspect':'square','voice_effect':'deep'}})
        assert result.status_code==200,result.text
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            p=client.get(base).json()
            new=[c for c in p['clips'] if c['id']!=old['id']]
            if new and all(c['status'] not in ('queued','rendering') for c in new):break
            time.sleep(.1)
        assert new and all(c['status']=='ready' for c in new),p
        assert p['clips'][0]['status']=='draft'
        assert all(c['voice_effect']=='deep' for c in new)
        exported=client.get(base+'/media/'+new[0]['id'])
        assert exported.status_code==200 and 'inline' in exported.headers['content-disposition']
        assert client.delete(base+'/clips/'+new[0]['id']).status_code==204
        assert client.get(base+'/media/'+new[0]['id']).status_code==404
        assert client.get(base+'/media/source').status_code==200
        assert client.post(base+'/highlights',json={'generated_settings':{'voice_effect':'invented'}}).status_code==422

@pytest.mark.parametrize('field,value',[('sticker_duration',0),('sticker_at',-1),('voice_strength',1.1),('source_caption_y',99)])
def test_new_control_bounds_are_validated(field,value):
    with pytest.raises(ValueError):main.EffectSettings(**{field:value})
