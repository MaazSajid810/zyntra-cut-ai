"""Native scripts choose bundled fonts and produce actual captioned MP4 pixels."""
import av
import numpy as np
import pytest
from backend import main,media


@pytest.mark.parametrize('text,family',[
    ('ਤੁਸੀਂ ਕਿਵੇਂ ਹੋ','Noto Sans Gurmukhi'),
    ('আপনি কেমন আছেন','Noto Sans Bengali'),
    ('توهان ڪيئن آهيو','Noto Sans Arabic'),
    ('تاسو څنګه یاست','Noto Sans Arabic'),
    ('Hola, ¿cómo estás?','Poppins'),
])
def test_native_caption_fonts_reach_real_export(tmp_path,text,family):
    source=tmp_path/'source.mp4'
    media.run(['-f','lavfi','-i','color=c=black:s=320x180:r=10','-t','1','-c:v','libx264',str(source)])
    clip={**main.EffectSettings(style='clean',aspect='original',render_quality='fast',caption_mode='phrase',caption_animation='none').model_dump(),
          'id':'native','start':0,'end':1}
    output=tmp_path/'captioned.mp4'
    segments=[{'id':0,'start':0,'end':1,'text':text}]
    media.render(source,tmp_path,clip,segments,output)
    ass=next(tmp_path.glob('*.ass')).read_text(encoding='utf-8')
    assert f'Style: Default,{family},' in ass
    assert text in ass
    with av.open(str(output)) as container:
        frame=next(container.decode(video=0)).to_ndarray(format='rgb24')
    assert np.count_nonzero(frame.max(axis=2)>80)>100
    assert media.probe(output)['duration']==pytest.approx(1,abs=.15)
