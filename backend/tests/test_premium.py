import av
import numpy as np
import pytest
from backend import main,media,captions

@pytest.fixture(scope='module')
def footage(tmp_path_factory):
    path=tmp_path_factory.mktemp('premium')/'source.mp4'
    media.run(['-f','lavfi','-i','testsrc2=size=320x180:rate=20','-f','lavfi','-i','sine=frequency=440:sample_rate=48000','-t','2','-c:v','libx264','-c:a','aac',str(path)])
    return path

WORDS=[{'start':0,'end':.5,'word':'Real'},{'start':.5,'end':1,'word':'timed'},{'start':1,'end':1.5,'word':'words.'}]
SEGMENTS=[{'start':0,'end':1.5,'text':'Real timed words.','words':WORDS}]

@pytest.mark.parametrize('mode',['karaoke','word'])
@pytest.mark.parametrize('animation',['none','pop','bounce','scale','fade'])
def test_word_captions_actually_render(footage,tmp_path,mode,animation):
    output=tmp_path/'premium.mp4'
    settings={**main.EffectSettings().model_dump(),'id':'premium','start':0,'end':1.5,'aspect':'square','render_quality':'fast','caption_mode':mode,'caption_animation':animation,'speed':1.2}
    media.render(footage,tmp_path,settings,SEGMENTS,output)
    assert media.probe(output)['duration']==pytest.approx(1.25,abs=.1)
    ass=next(tmp_path.glob('*.ass')).read_text(encoding='utf-8')
    assert ass.count('Dialogue: 0,')==3
    assert '0:00:00.42,0:00:00.83,Default' in ass
    if mode=='karaoke':assert r'\1c&H35dfff&' in ass
    with av.open(str(output)) as container:
        frames=list(container.decode(video=0))
        assert len(frames)>10
        # Captions land in the black padded lower safe zone, not only in ASS text.
        pixels=frames[4].to_ndarray(format='rgb24')
        assert (pixels[350:430].max(axis=2)>120).sum()>200

@pytest.mark.parametrize('zoom',['gentle','punch'])
def test_motion_and_audio_are_real_filters(footage,tmp_path,zoom):
    settings={**main.EffectSettings().model_dump(),'id':'motion','start':0,'end':1.5,'aspect':'square','render_quality':'fast','style':'none','zoom':zoom,'audio_leveling':True,'denoise':True}
    out=tmp_path/'motion.mp4'
    media.render(footage,tmp_path,settings,[],out)
    assert media.probe(out)['has_audio']
    assert media.probe(out)['duration']==pytest.approx(1.5,abs=.1)

def test_legacy_follow_requires_explicit_permission(footage,tmp_path):
    settings={**main.EffectSettings().model_dump(),'id':'legacy','start':0,'end':1,'style':'none','sticker':'follow','render_quality':'fast'}
    media.render(footage,tmp_path,settings,[],tmp_path/'clean.mp4')
    assert not list(tmp_path.glob('*.ass'))
    settings['sticker_enabled']=True
    media.render(footage,tmp_path,settings,[],tmp_path/'follow.mp4')
    assert 'FOLLOW' in next(tmp_path.glob('*.ass')).read_text(encoding='utf-8')

def test_default_settings_preserve_source_and_no_branding():
    s=main.EffectSettings()
    assert s.aspect=='original' and s.render_quality=='high'
    assert s.subtitle_font=='Poppins' and s.subtitle_size>=50
    assert s.sticker=='none' and not s.sticker_enabled
    assert not s.overlay_text

def test_editing_text_invalidates_word_alignment():
    assert captions.aligned(SEGMENTS[0])
    assert not captions.aligned({**SEGMENTS[0],'text':'Different edited words.'})
