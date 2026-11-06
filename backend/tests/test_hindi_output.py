from types import SimpleNamespace
from contextlib import nullcontext
import sys
import pytest
from fastapi.testclient import TestClient
from backend import main,store,guest,speech,romanization,captions,media


def hindi_segment():
    return {'id':0,'start':0,'end':3,'text':'मैं ठीक हूँ।','words':[
        {'word':'मैं','start':0,'end':1},{'word':' ठीक','start':1,'end':2},{'word':' हूँ।','start':2,'end':3}]}


@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DATA',tmp_path)
    with TestClient(main.app) as c:
        c.get('/api/session')
        store.save({'id':'hindi-test','owner_id':guest.owner_for_token(c.cookies.get(guest.COOKIE)),
                    'status':'ready','has_audio':True,'duration':3,'language':'ur','caption_script':'roman_urdu',
                    'transcript':[{'id':0,'start':0,'end':3,'text':'main theek hoon.'}],
                    'source_transcript':[{'id':0,'start':0,'end':3,'text':'میں ٹھیک ہوں۔'}],
                    'clips':[{'id':'existing','title':'Existing clip','start':0,'end':3,'status':'ready','file':'old.mp4','score':88}]})
        yield c


def install_recognition_fixture(monkeypatch,end=3):
    # Explicit model unit fixture; actual Urdu/Hindi audio is tested separately.
    calls=[]
    monkeypatch.setattr(speech,'timeline_audio',lambda source:nullcontext(source))
    monkeypatch.setattr(main.pool,'submit',lambda *args:calls.append(args))
    monkeypatch.setattr(main,'model',object())
    monkeypatch.setitem(main.models,'small',object())
    segment=hindi_segment()
    segment['end']=end
    for word in segment['words']:
        word['start']*=end/3;word['end']*=end/3
    def recognize(*args,**options):
        assert options=={'caption_script':'hindi'}
        s=SimpleNamespace(**{**segment,'words':[SimpleNamespace(**w) for w in segment['words']]})
        return iter([s]),SimpleNamespace(language='hi')
    monkeypatch.setattr(speech,'transcribe',recognize)
    return calls


def test_apply_hindi_runs_real_audio_job_path_and_keeps_ranges(client,monkeypatch):
    calls=install_recognition_fixture(monkeypatch)
    r=client.post('/api/projects/hindi-test/transcript/script',json={'caption_script':'hindi'})
    assert r.status_code==202 and len(calls)==1
    assert r.json()['status']=='queued'
    main.process('hindi-test')
    p=client.get('/api/projects/hindi-test').json()
    assert p['status']=='ready' and p['caption_script']=='hindi'
    assert p['transcript'][0]['text']=='मैं ठीक हूँ।' and captions.aligned(p['transcript'][0])
    assert len(p['clips'])==1 and (p['clips'][0]['start'],p['clips'][0]['end'])==(0,3)
    assert p['clips'][0]['status']=='draft' and p['clips'][0]['file'] is None
    assert 'मैं ठीक हूँ।' in client.get('/api/projects/hindi-test/subtitles').text
    assert 'मैं ठीक हूँ।' in client.get('/api/projects/hindi-test/subtitles?format=vtt').text


def test_generate_hindi_from_roman_transcribes_and_generates_a_new_batch(client,monkeypatch):
    calls=install_recognition_fixture(monkeypatch,end=2.3)
    # Keep the old clip outside the recognized speech.
    store.mutate('hindi-test',lambda p:p['clips'][0].update(start=2.4,end=3))
    r=client.post('/api/projects/hindi-test/highlights',json={'caption_script':'hindi','clip_count':1,'selection_mode':'all'})
    assert r.status_code==202 and len(calls)==1
    main.process('hindi-test')
    p=client.get('/api/projects/hindi-test').json()
    assert p['status']=='ready' and p['clip_generation']['created']==1
    assert len(p['clips'])==2 and p['clips'][0]['id']=='existing'
    assert p['clips'][0]['status']=='draft' and p['clips'][0]['start']==2.4


def test_hindi_roman_hindi_switch_uses_immutable_native_snapshot(client,monkeypatch):
    queued=[];monkeypatch.setattr(main.pool,'submit',lambda *args:queued.append(args))
    store.mutate('hindi-test',lambda p:p.update(caption_script='hindi',source_transcript=[hindi_segment()],transcript=[hindi_segment()]))
    url='/api/projects/hindi-test/transcript/script'
    p=client.post(url,json={'caption_script':'roman_urdu'}).json()
    assert p['transcript'][0]['text']=='main theek hoon.'
    assert p['source_transcript']==[hindi_segment()]
    r=client.post(url,json={'caption_script':'hindi'})
    assert r.status_code==200 and not queued
    assert r.json()['transcript']==[hindi_segment()]


def test_hindi_conversion_never_labels_urdu_text_as_devanagari():
    assert romanization.convert_segments([hindi_segment()],'hindi')==[hindi_segment()]
    with pytest.raises(ValueError):romanization.convert_segments([{'text':'آپ کیسے ہیں؟'}],'hindi')


@pytest.mark.parametrize('language',[None,'auto'])
@pytest.mark.parametrize('text,script,expected',[
    ('मैं ठीक हूँ।','hindi','मैं ठीक हूँ।'),
    ('मैं ठीक हूँ।','roman_urdu','main theek hoon.'),
    ('میں ٹھیک ہوں۔','roman_urdu','main theek hoon.'),
])
def test_manual_native_captions_without_detected_language_keep_script_and_source(client,monkeypatch,language,text,script,expected):
    from copy import deepcopy
    source=[{'id':0,'start':0,'end':3,'text':text}]
    store.mutate('hindi-test',lambda p:p.update(language=language,caption_script='original',source_transcript=deepcopy(source),transcript=deepcopy(source)))
    def no_recognition(*args):pytest.fail('Manual text conversion must not run speech recognition.')
    monkeypatch.setattr(main.pool,'submit',no_recognition)
    response=client.post('/api/projects/hindi-test/transcript/script',json={'caption_script':script})
    assert response.status_code==200,response.text
    saved=response.json()
    assert saved['caption_script']==script and saved['caption_warning'] is None
    assert saved['transcript'][0]['text']==expected
    assert saved['source_transcript']==source and saved['language']==language
    assert (saved['clips'][0]['start'],saved['clips'][0]['end'])==(0,3)


@pytest.mark.parametrize('language,text',[
    ('mr','मैं ठीक हूँ।'),
    (None,'An English manual caption.'),
])
def test_manual_script_support_does_not_invent_a_translation_route(language,text,tmp_path,monkeypatch):
    from backend import translation
    monkeypatch.setattr(translation,'ROOT',tmp_path/'uninstalled-models')
    source=[{'id':0,'start':0,'end':3,'text':text}]
    converted,script,warning=main.caption_conversion(source,language,'hindi')
    assert converted==source and script=='original' and 'unavailable' in warning


@pytest.mark.parametrize('mode',['fast','balanced','accurate'])
def test_hindi_recognition_biases_script_and_blocks_split_arabic_tokens(monkeypatch,mode):
    calls=[]
    class Tokenizer:
        def get_vocab(self):return {'Ø§':10,'Ù':11,'Hindi':12,'à¤':13,'hello':14}
        def decode(self,ids):return {10:'ا',11:'�',12:'हिंदी',13:'�',14:'hello'}[ids[0]]
    class Recognizer:
        hf_tokenizer=Tokenizer()
        def transcribe(self,*args,**options):calls.append(options)
    class Pipeline(Recognizer):
        def __init__(self,model):pass
    monkeypatch.setitem(sys.modules,'faster_whisper',SimpleNamespace(BatchedInferencePipeline=Pipeline))
    speech.transcribe(Recognizer(),'source',mode,language='ur',caption_script='hindi')
    opts=calls[0]
    assert opts['language']=='hi' and opts['word_timestamps'] is True
    assert opts['suppress_tokens']==[-1,10,11]
    assert opts['task']=='transcribe' and 'initial_prompt' not in opts


def test_hindi_font_is_selected_for_actual_ass_output(tmp_path):
    path=tmp_path/'hindi.ass'
    media.write_ass(path,[hindi_segment()],0,3,'clean',640,360,{'caption_mode':'karaoke'})
    text=path.read_text(encoding='utf-8')
    assert 'Noto Sans Devanagari' in text and 'मैं' in text
    assert (media.FONTS/'NotoSansDevanagari.ttf').is_file()
