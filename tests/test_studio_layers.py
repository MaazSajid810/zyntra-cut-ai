import io
import time

import av
import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend import main,media,store,speech,assets


@pytest.fixture
def studio(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DATA',tmp_path)
    source=tmp_path/'fixture.mp4'
    media.run(['-f','lavfi','-i','color=c=0x204080:s=320x180:r=30','-f','lavfi','-i','sine=frequency=440:sample_rate=48000','-t','4','-c:v','libx264','-c:a','aac',str(source)])
    with TestClient(main.app) as client:
        client.get('/api/session')
        with source.open('rb') as f:p=client.post('/api/projects',files={'file':('studio.mp4',f,'video/mp4')}).json()
        yield client,p,tmp_path/p['id'],source


def upload(client,p,kind,name,data):
    r=client.post(f"/api/projects/{p['id']}/assets?kind={kind}",files={'file':(name,data)})
    assert r.status_code==201,r.text
    return r.json()


def logo_bytes():
    data=io.BytesIO();image=Image.new('RGBA',(80,40),(255,0,0,255));image.putpixel((0,0),(0,0,0,0));image.save(data,format='PNG');return data.getvalue()


def frame(path,at=1):
    with av.open(str(path)) as container:
        return next(f for f in container.decode(video=0) if f.time>=at).to_ndarray(format='rgb24').astype(float)


def render(studio,name,**changes):
    _,_,folder,source=studio
    options={'id':name,'start':0,'end':4,**main.EffectSettings(style='none',render_quality='fast').model_dump(),**changes}
    output=folder/(name+'.mp4')
    media.render(source,folder,options,[],output,assets=store.get(studio[1]['id']).get('assets',[]))
    return output


def test_logo_upload_ownership_reference_validation_and_deletion(studio):
    client,p,folder,_=studio;asset=upload(client,p,'logo','logo.png',logo_bytes());base=f"/api/projects/{p['id']}"
    assert client.get(base+'/assets').json()[0]['id']==asset['id']
    assert client.get(base+'/assets/'+asset['id']).status_code==200
    with TestClient(main.app) as other:
        other.get('/api/session')
        assert other.get(base+'/assets').status_code==404
        assert other.get(base+'/assets/'+asset['id']).status_code==404
        assert other.delete(base+'/assets/'+asset['id']).status_code==404
    body={'title':'Branded','start':0,'end':3,'logo_asset_id':asset['id']}
    assert client.post(base+'/clips',json={**body,'logo_asset_id':'f'*32}).status_code==400
    assert client.post(base+'/highlights',json={'generated_settings':{'logo_asset_id':'f'*32}}).status_code==400
    clip=client.post(base+'/clips',json=body).json()['clips'][0]
    assert client.delete(base+'/assets/'+asset['id']).status_code==409
    assert client.delete(base+'/clips/'+clip['id']).status_code==204
    assert client.delete(base+'/assets/'+asset['id']).status_code==204
    assert not (folder/asset['file']).exists()
    assert client.get(base+'/media/source').status_code==200


def test_invalid_logo_is_not_registered_or_retained(studio):
    client,p,folder,_=studio
    r=client.post(f"/api/projects/{p['id']}/assets?kind=logo",files={'file':('bad.svg',b'<svg><script>alert(1)</script></svg>')})
    assert r.status_code==400
    assert not list(folder.glob('asset-*'))
    data=io.BytesIO();Image.new('RGB',(4100,10)).save(data,format='PNG')
    r=client.post(f"/api/projects/{p['id']}/assets?kind=logo",files={'file':('huge.png',data.getvalue())})
    assert r.status_code==400 and '4096' in r.text


def test_text_watermark_opacity_and_position_are_in_actual_export(studio):
    baseline=frame(render(studio,'plain'))
    faint=frame(render(studio,'faint',watermark_enabled=True,watermark_text='MY CHANNEL',watermark_opacity=.2,watermark_x=0,watermark_y=0))
    strong=frame(render(studio,'strong',watermark_enabled=True,watermark_text='MY CHANNEL',watermark_opacity=1,watermark_x=0,watermark_y=0))
    moved=frame(render(studio,'moved',watermark_enabled=True,watermark_text='MY CHANNEL',watermark_opacity=1,watermark_x=100,watermark_y=100))
    assert np.abs(strong-baseline).sum()>np.abs(faint-baseline).sum()*2.5
    assert np.abs(strong[:55]-baseline[:55]).sum()>np.abs(strong[90:]-baseline[90:]).sum()*5
    assert np.abs(moved[90:]-baseline[90:]).sum()>np.abs(moved[:55]-baseline[:55]).sum()*5
    disabled=frame(render(studio,'disabled',watermark_enabled=False,watermark_text='NEVER AUTOMATIC'))
    assert np.abs(disabled-baseline).mean()<.1


def test_uploaded_logo_is_composited_with_opacity_and_bounds(studio):
    client,p,_,_=studio;asset=upload(client,p,'logo','logo.png',logo_bytes())
    result=frame(render(studio,'logo',logo_asset_id=asset['id'],logo_width=25,logo_x=100,logo_y=100,logo_opacity=1))
    red=(result[:,:,0]>180)&(result[:,:,1]<50)
    ys,xs=np.where(red)
    assert len(xs)>1500 and xs.min()>230 and ys.min()>130
    faded=frame(render(studio,'logo-faded',logo_asset_id=asset['id'],logo_width=25,logo_x=100,logo_y=100,logo_opacity=.2))
    assert faded[160,280,0]<result[160,280,0]*.5


@pytest.mark.parametrize('transition,expected',[('fade','dark'),('white','light')])
def test_transitions_are_present_at_both_ends(studio,transition,expected):
    output=render(studio,'transition-'+transition,transition=transition,transition_duration=.4)
    beginning=frame(output,0)[90,160].mean();middle=frame(output,2)[90,160].mean();ending=frame(output,3.95)[90,160].mean()
    assert middle==pytest.approx(74,abs=10)
    if expected=='dark':assert beginning<5 and ending<20
    else:assert beginning>245 and ending>230


def samples(path):
    with av.open(str(path)) as container:
        resampler=av.AudioResampler(format='fltp',layout='mono',rate=16000)
        return np.concatenate([part.to_ndarray().reshape(-1) for f in container.decode(audio=0) for part in resampler.resample(f)])


def test_broll_loops_only_in_its_time_range_and_keeps_source_speech(studio,tmp_path):
    client,p,_,_=studio;filler=tmp_path/'broll.mp4'
    media.run(['-f','lavfi','-i','color=c=lime:s=160x90:r=30','-t','0.5','-c:v','libx264',str(filler)])
    asset=upload(client,p,'filler','broll.mp4',filler.read_bytes())
    output=render(studio,'filler',filler_asset_id=asset['id'],filler_start=1,filler_end=3,transition='fade',transition_duration=.15)
    assert frame(output,.5)[20,20,2]>90
    assert frame(output,2)[20,20,1]>230
    assert frame(output,3.5)[20,20,2]>90
    audio=samples(output)[16000:32000];peak=np.fft.rfftfreq(len(audio),1/16000)[np.abs(np.fft.rfft(audio)).argmax()]
    assert peak==pytest.approx(440,abs=8)
    assert media.probe(output)['duration']==pytest.approx(4,abs=.12)


@pytest.mark.parametrize('sound',['pop','ding','whoosh'])
def test_synthesized_sounds_have_real_audio_and_scheduled_onset(studio,sound):
    output=render(studio,'sound-'+sound,voice_effect='mute',sound_effect=sound,sound_at=1,sound_volume=.8)
    audio=samples(output)
    assert np.abs(audio[:12000]).mean()<.0005
    assert np.abs(audio[16500:18500]).mean()>.0008


def test_uploaded_background_music_and_api_timing_validation(studio,tmp_path):
    client,p,_,_=studio;music=tmp_path/'music.wav'
    media.run(['-f','lavfi','-i','sine=frequency=220:sample_rate=48000','-t','0.6',str(music)])
    asset=upload(client,p,'music','music.wav',music.read_bytes())
    output=render(studio,'music',music_asset_id=asset['id'],music_volume=.5,voice_effect='mute',sound_effect='ding',sound_at=2)
    audio=samples(output)[16000:24000];peak=np.fft.rfftfreq(len(audio),1/16000)[np.abs(np.fft.rfft(audio)).argmax()]
    assert peak==pytest.approx(220,abs=8)
    response=client.post(f"/api/projects/{p['id']}/clips",json={'title':'Bad timing','start':0,'end':1,'sound_effect':'pop','sound_at':2})
    assert response.status_code==400


def test_small_model_is_used_for_roman_urdu_without_translation():
    for mode in ('fast','balanced','accurate'):
        assert speech.model_name(mode,'roman_urdu','auto')=='small'
        assert speech.model_name(mode,'roman_urdu','ur')=='small'
    assert speech.model_name('fast','roman_urdu','en')=='tiny'


def test_asset_limits_and_named_broll_rejection_cleanup(studio,monkeypatch):
    client,p,folder,_=studio
    limits=client.get('/api/assets/limits').json()
    assert limits['filler']=={'max_bytes':100*1024**2,'label':'B-roll video'}
    assert limits['image']['max_bytes']==20*1024**2
    monkeypatch.setitem(assets.LIMITS,'filler',1024)
    r=client.post(f"/api/projects/{p['id']}/assets?kind=filler",files={'file':('large.mp4',bytes(1025))})
    assert r.status_code==413 and 'B-roll video' in r.json()['detail']
    assert not list(folder.glob('asset-*')) and not client.get(f"/api/projects/{p['id']}/assets").json()


def test_photo_ownership_reference_validation_and_deletion(studio):
    client,p,folder,_=studio;base=f"/api/projects/{p['id']}"
    photo=upload(client,p,'image','photo.webp',logo_bytes())
    assert photo['kind']=='image' and photo['file'].endswith('.png')
    assert client.get(base+'/assets/'+photo['id']).headers['content-type']=='image/png'
    with TestClient(main.app) as other:
        other.get('/api/session')
        assert other.get(base+'/assets/'+photo['id']).status_code==404
    body={'title':'Photo clip','start':0,'end':3,'image_asset_id':photo['id']}
    assert client.post(base+'/clips',json={**body,'image_asset_id':'f'*32}).status_code==400
    assert client.post(base+'/clips',json={**body,'image_start':3,'image_end':4}).status_code==400
    assert client.post(base+'/clips',json={**body,'image_start':1,'image_end':.5}).status_code==422
    clip=client.post(base+'/clips',json=body).json()['clips'][0]
    assert client.delete(base+'/assets/'+photo['id']).status_code==409
    assert client.delete(base+'/clips/'+clip['id']).status_code==204
    assert client.delete(base+'/assets/'+photo['id']).status_code==204
    assert client.get(base+'/media/source').status_code==200


def test_invalid_or_oversized_photo_is_cleaned_up(studio):
    client,p,folder,_=studio;base=f"/api/projects/{p['id']}"
    assert client.post(base+'/assets?kind=image',files={'file':('bad.svg',b'<svg><script>alert(1)</script></svg>')}).status_code==400
    data=io.BytesIO();Image.new('RGB',(4097,10)).save(data,format='PNG')
    assert client.post(base+'/assets?kind=image',files={'file':('too-wide.png',data.getvalue())}).status_code==400
    assert not list(folder.glob('asset-*'))


def test_photo_timing_opacity_position_and_source_audio_in_real_mp4(studio):
    client,p,_,_=studio;photo=upload(client,p,'image','photo.png',logo_bytes())
    settings={'image_asset_id':photo['id'],'image_start':1,'image_end':3,'image_width':25,'image_x':100,'image_y':100}
    output=render(studio,'photo',**settings)
    image=frame(output,2);mask=(image[:,:,0]>180)&(image[:,:,1]<50)
    ys,xs=np.where(mask)
    assert len(xs)>1500 and xs.min()>230 and ys.min()>130
    for at in (.5,3.5):assert frame(output,at)[160,280,2]>90
    faded=frame(render(studio,'photo-faint',**settings,image_opacity=.2),2)
    assert faded[160,280,0]<image[160,280,0]*.5
    audio=samples(output)[16000:32000];peak=np.fft.rfftfreq(len(audio),1/16000)[np.abs(np.fft.rfft(audio)).argmax()]
    assert peak==pytest.approx(440,abs=8)
    assert media.probe(output)['duration']==pytest.approx(4,abs=.12)


@pytest.mark.parametrize('fit',['contain','cover'])
def test_full_frame_photo_fit_in_actual_mp4(studio,fit):
    client,p,_,_=studio;photo=upload(client,p,'image','photo.png',logo_bytes())
    result=frame(render(studio,'photo-full-'+fit,image_asset_id=photo['id'],image_layout='full',image_fit=fit))
    assert result[90,160,0]>220 and result[90,160,1]<40
    if fit=='contain':assert result[2,160].mean()<15
    else:assert result[2,160,0]>220


@pytest.mark.parametrize('format',['PNG','JPEG','WEBP'])
def test_actual_photo_formats_are_normalized_and_jpeg_orientation_is_respected(studio,format):
    client,p,folder,_=studio;data=io.BytesIO();image=Image.new('RGB',(40,80),(255,0,0))
    options={}
    if format=='JPEG':
        exif=Image.Exif();exif[274]=6;options['exif']=exif
    image.save(data,format=format,**options)
    photo=upload(client,p,'image','photo.'+format.lower(),data.getvalue())
    expected=(80,40) if format=='JPEG' else (40,80)
    assert (photo['width'],photo['height'])==expected
    with Image.open(folder/photo['file']) as normalized:
        assert normalized.format=='PNG' and normalized.mode=='RGBA' and normalized.size==expected


def test_truncated_photo_returns_readable_400_and_no_partial_asset(studio):
    client,p,folder,_=studio;data=io.BytesIO();Image.new('RGB',(100,100)).save(data,format='JPEG')
    response=client.post(f"/api/projects/{p['id']}/assets?kind=image",files={'file':('broken.jpg',data.getvalue()[:-30])})
    assert response.status_code==400 and 'decoded' in response.json()['detail']
    assert not list(folder.glob('asset-*'))
