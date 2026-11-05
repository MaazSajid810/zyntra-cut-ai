"""Neon presets must change real exported pixels and respect word timing."""
import av
import numpy as np
import pytest
from backend import main,media


def transcript():
    return [{'id':0,'start':0,'end':2,'text':'Neon Words','words':[
        {'word':'Neon','start':0,'end':1},{'word':' Words','start':1,'end':2}]}]


def pixels(path,second):
    with av.open(str(path)) as container:
        for frame in container.decode(video=0):
            if frame.time>=second:return frame.to_ndarray(format='rgb24').astype(float)
    raise AssertionError('The rendered video ended before the requested frame.')


@pytest.fixture
def source(tmp_path):
    path=tmp_path/'source.mp4'
    media.run(['-f','lavfi','-i','color=c=black:s=320x180:r=15','-t','2','-c:v','libx264',str(path)])
    return path


def settings(style,mode='karaoke'):
    return {**main.EffectSettings(style=style,caption_mode=mode,caption_animation='none',
            aspect='original',render_quality='fast',subtitle_position='center',subtitle_size=64,
            highlight_color='#25f5d0').model_dump(),'id':'neon-test','start':0,'end':2}


def test_neon_glow_renders_a_halo_beyond_flat_pink_text(source,tmp_path):
    output=tmp_path/'glow.mp4';baseline=tmp_path/'flat.mp4'
    media.render(source,tmp_path,settings('neon','phrase'),transcript(),output)
    flat={**settings('clean','phrase'),'subtitle_color':'#fc78f1'}
    media.render(source,tmp_path,flat,transcript(),baseline)
    glow=pixels(output,.3);plain=pixels(baseline,.3)
    pink=(glow[:,:,0]>50)&(glow[:,:,2]>40)&(glow[:,:,0]>glow[:,:,1]*1.2)
    absent=plain.max(axis=2)<15
    assert np.count_nonzero(pink&absent)>30
    assert any('Dialogue: -1,' in p.read_text(encoding='utf-8') and ',Glow,' in p.read_text(encoding='utf-8') for p in tmp_path.glob('*.ass'))


def test_neon_active_word_moves_with_actual_speech_timing(source,tmp_path):
    output=tmp_path/'highlight.mp4'
    media.render(source,tmp_path,settings('neon_highlight'),transcript(),output)
    early=pixels(output,.3);late=pixels(output,1.3)
    def active(frame):return (frame[:,:,1]>100)&(frame[:,:,1]>frame[:,:,0]+45)&(frame[:,:,1]>frame[:,:,2]+15)
    first,second=active(early),active(late)
    midpoint=early.shape[1]//2
    assert first[:,:midpoint].sum()>first[:,midpoint:].sum()+20
    assert second[:,midpoint:].sum()>second[:,:midpoint].sum()+20
    ass=next(tmp_path.glob('*.ass')).read_text(encoding='utf-8')
    assert r'\3c&H' in ass and r'\blur0.6' in ass


def test_unaligned_neon_highlight_uses_phrase_fallback(source,tmp_path):
    output=tmp_path/'fallback.mp4'
    segment={'id':0,'start':0,'end':2,'text':'Edited neon phrase'}
    media.render(source,tmp_path,settings('neon_highlight'),[segment],output)
    ass=next(tmp_path.glob('*.ass')).read_text(encoding='utf-8')
    assert 'Edited neon phrase' in ass and ',Glow,' in ass
    assert 'words' not in segment
    assert media.probe(output)['duration']==pytest.approx(2,abs=.15)
