import time
import av
import numpy as np
import pytest
from fastapi.testclient import TestClient
from backend import main,media,store,compositor


@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DATA',tmp_path)
    with TestClient(main.app) as client:
        client.get('/api/session');yield client


def samples(path):
    with av.open(str(path)) as container:
        resampler=av.AudioResampler(format='s16',layout='mono',rate=48000)
        return np.concatenate([out.to_ndarray().reshape(-1) for frame in container.decode(audio=0) for out in resampler.resample(frame)])


@pytest.mark.parametrize('name',list(compositor.SOUNDS))
def test_real_sound_preview_and_render_use_same_effect_at_requested_time(client,tmp_path,name):
    preview=client.get('/api/sound-effects/'+name)
    assert preview.status_code==200 and preview.headers['content-type']=='audio/wav'
    assert client.get('/api/sound-effects/'+name,headers={'Range':'bytes=0-99'}).status_code==206
    assert np.max(np.abs(samples(tmp_path/'sound-effects'/(name+'.wav'))))>100
    source=tmp_path/'silent.mp4';output=tmp_path/(name+'-render.mp4')
    media.run(['-f','lavfi','-i','color=c=blue:s=160x90:r=15','-t','2','-c:v','libx264',str(source)])
    clip={**main.EffectSettings(sound_effect=name,sound_at=.4,sound_volume=.5,style='none',render_quality='fast').model_dump(),'id':'effect','start':0,'end':2}
    media.render(source,tmp_path,clip,[],output)
    pcm=samples(output)
    assert np.max(np.abs(pcm[:int(.35*48000)]))<20
    assert np.max(np.abs(pcm[int(.4*48000):int(1.5*48000)]))>100
    assert np.max(np.abs(pcm[int(1.7*48000):int(1.95*48000)]))<20
    assert media.probe(output)['duration']==pytest.approx(2,abs=.15)


def test_unknown_effect_is_rejected_and_requires_a_guest(client):
    assert client.get('/api/sound-effects/unknown').status_code==422
    assert TestClient(main.app).get('/api/sound-effects/ding').status_code==401
