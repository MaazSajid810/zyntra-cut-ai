import re
import wave
import numpy as np
import pytest
from backend import media,speech,main,translation,captions


@pytest.mark.parametrize('offset',[-.4,.6])
def test_caption_sync_uses_output_seconds_at_double_speed_and_leaves_branding(tmp_path,offset):
    segments=[{'id':0,'start':2,'end':4,'text':'One two','words':[{'word':'One','start':2,'end':3},{'word':' two','start':3,'end':4}]}]
    path=tmp_path/'sync.ass'
    media.write_ass(path,segments,0,8,'clean',640,360,{'speed':2,'caption_offset':offset,'caption_mode':'word','overlay_text':'Channel'})
    text=path.read_text(encoding='utf-8')
    assert f'Dialogue: 0,{media.stamp(1+offset)},{media.stamp(1.5+offset)}' in text
    assert 'Dialogue: 1,0:00:00.00,0:00:04.00' in text
    srt=media.subtitle_file(segments,'srt',0,8,2,offset)
    assert f'00:00:0{1+offset:.3f}'.replace('.',',') in srt
    assert segments[0]['start']==2 and segments[0]['words'][0]['start']==2


def test_sync_clamps_caption_events_to_clip_bounds(tmp_path):
    s=[{'id':0,'start':0,'end':1,'text':'Start'},{'id':1,'start':3,'end':4,'text':'End'}]
    early=media.subtitle_file(s,'vtt',0,4,1,-.5)
    late=media.subtitle_file(s,'srt',0,4,1,.5)
    assert '00:00:00.000 --> 00:00:00.500' in early
    assert '00:00:03,500 --> 00:00:04,000' in late
    with pytest.raises(ValueError):main.EffectSettings(caption_offset=6)


def onset(path):
    import av
    with av.open(str(path)) as container:
        frames=list(container.decode(audio=0))
        samples=np.concatenate([f.to_ndarray().reshape(-1) for f in frames])
        rate=frames[0].sample_rate
    threshold=np.max(np.abs(samples))*.1
    return np.flatnonzero(np.abs(samples)>threshold)[0]/rate


def test_real_timestamp_delayed_audio_stays_in_sync_in_asr_input_and_export(tmp_path):
    source=tmp_path/'delayed.mp4'
    media.run(['-f','lavfi','-i','color=c=blue:s=320x180:r=30','-itsoffset','0.8','-f','lavfi','-i','sine=frequency=440:sample_rate=16000:duration=2','-t','3','-c:v','libx264','-c:a','aac',str(source)])
    with speech.timeline_audio(source) as wav:
        assert onset(wav)==pytest.approx(.8,abs=.08)
        temp=wav
    assert not temp.exists()
    clip={**main.EffectSettings(style='none',speed=2,render_quality='fast').model_dump(),'id':'delayed','start':0,'end':3}
    output=tmp_path/'output.mp4'
    media.render(source,tmp_path,clip,[],output)
    assert onset(output)==pytest.approx(.4,abs=.08)


@pytest.mark.parametrize('script',['urdu','hindi','roman_urdu'])
def test_real_local_translation_preserves_sentence_timing_without_false_word_alignment(script):
    if not (translation.ROOT/'en_ur'/'model'/'model.bin').exists() or not (translation.ROOT/'en_hi'/'model'/'model.bin').exists():
        pytest.skip('Run scripts.setup_translation to install real translation models')
    original=[{'id':0,'start':1.2,'end':4.5,'text':'Hello, how are you?','words':[{'word':'Hello,','start':1.2,'end':2},{'word':' how are you?','start':2,'end':4.5}]}]
    result=translation.convert_segments(original,'en',script)
    assert result[0]['text'] and result[0]['text']!=original[0]['text']
    assert '\u2581' not in result[0]['text'] and len(result[0]['text'].split())>1
    assert (result[0]['start'],result[0]['end'])==(1.2,4.5)
    assert result[0]['timing']=='translated_sentence' and 'words' not in result[0]
    assert not captions.aligned(result[0])
    if script=='urdu':assert re.search(r'[\u0600-\u06ff]',result[0]['text'])
    elif script=='hindi':assert re.search(r'[\u0900-\u097f]',result[0]['text'])
    else:assert not re.search(r'[\u0600-\u06ff\u0900-\u097f]',result[0]['text'])


def test_missing_negation_is_flagged_for_review_without_inventing_a_correction(monkeypatch):
    monkeypatch.setattr(translation,'translate_texts',lambda *args:['آپ پوچھیں۔'])
    output=translation.convert_segments([{'id':0,'start':0,'end':3,'text':'Do not ask.'}],'en','urdu')[0]
    assert output['source_text']=='Do not ask.' and output['translation_warning']
    assert output['text']=='آپ پوچھیں۔'
