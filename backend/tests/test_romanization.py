from copy import deepcopy
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from backend import main,store,guest,romanization,captions,speech


def urdu_segment():
    words=['میں','ٹھیک','ہوں۔']
    return {'id':0,'start':0,'end':3,'text':' '.join(words),
            'words':[{'word':word,'start':i,'end':i+1} for i,word in enumerate(words)]}


def test_real_urdu_transliteration_preserves_alignment_and_original():
    source=[urdu_segment()]; original=deepcopy(source)
    result=romanization.convert_segments(source,'roman_urdu')
    assert result[0]['text']=='main theek hoon.'
    assert captions.aligned(result[0])
    assert [(w['start'],w['end']) for w in result[0]['words']]==[(0,1),(1,2),(2,3)]
    assert source==original


def test_hindi_and_mixed_english_are_romanized_without_translation():
    assert romanization.roman_text('आप कैसे हैं? मैं ठीक हूँ।')=='aap kaise hain? main theek hoon.'
    assert romanization.roman_text('میری YouTube video 1080p ہے۔').isascii()
    assert 'YouTube video 1080p' in romanization.roman_text('میری YouTube video 1080p ہے۔')
    assert romanization.roman_text('My English sentence stays unchanged!')=='My English sentence stays unchanged!'


def test_unaligned_text_is_converted_without_inventing_word_timing():
    segment=urdu_segment();segment['text']='آپ کیسے ہیں؟'
    result=romanization.convert_segments([segment],'roman_urdu')[0]
    assert 'words' not in result and not romanization.URDU.search(result['text'])
    assert romanization.convert_segments([segment],'original')==[segment]
    with pytest.raises(ValueError):romanization.convert_segments([segment],'invalid')


@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DATA',tmp_path)
    with TestClient(main.app) as c:
        c.get('/api/session')
        owner=guest.owner_for_token(c.cookies.get(guest.COOKIE))
        store.save({'id':'roman-test','owner_id':owner,'status':'ready','has_audio':True,'duration':3,
                    'language':'ur','transcript':[urdu_segment()],
                    'clips':[{'id':'clip','start':0,'end':3,'status':'ready','file':'old.mp4','score':88}]})
        yield c


def test_script_switch_restores_source_and_invalidates_only_exports(client):
    url='/api/projects/roman-test/transcript/script'
    p=client.post(url,json={'caption_script':'roman_urdu'}).json()
    assert p['transcript'][0]['text']=='main theek hoon.'
    assert p['source_transcript'][0]['text']=='میں ٹھیک ہوں۔'
    assert (p['clips'][0]['start'],p['clips'][0]['end'])==(0,3)
    assert p['clips'][0]['status']=='draft' and p['clips'][0]['file'] is None
    assert client.post(url,json={'caption_script':'roman_urdu'}).json()['transcript']==p['transcript']
    p=client.post(url,json={'caption_script':'original'}).json()
    assert p['transcript'][0]==urdu_segment()
    assert client.post(url,json={'caption_script':'fake'}).status_code==422


def test_script_change_cannot_overwrite_later_user_edits(client):
    base='/api/projects/roman-test'
    client.post(base+'/transcript/script',json={'caption_script':'roman_urdu'})
    changed={**urdu_segment(),'text':'Mera apna edited subtitle.'}
    assert client.put(base+'/transcript',json=[changed]).status_code==200
    assert client.post(base+'/transcript/script',json={'caption_script':'original'}).status_code==400
    assert client.get(base).json()['transcript'][0]['text']==changed['text']


def test_busy_and_guest_ownership_are_enforced(client):
    url='/api/projects/roman-test/transcript/script'
    token=client.cookies.get(guest.COOKIE)
    client.cookies.clear();client.get('/api/session')
    assert client.post(url,json={'caption_script':'roman_urdu'}).status_code==404
    client.cookies.clear();client.cookies.set(guest.COOKIE,token)
    store.mutate('roman-test',lambda p:p.update(status='transcribing'))
    assert client.post(url,json={'caption_script':'roman_urdu'}).status_code==409


def test_transcription_job_converts_words_before_generating(client,monkeypatch):
    from contextlib import nullcontext
    monkeypatch.setattr(speech,'timeline_audio',lambda source:nullcontext(source))
    calls=[]
    monkeypatch.setattr(main.pool,'submit',lambda *args:calls.append(args))
    monkeypatch.setitem(main.models,'small',object())
    monkeypatch.setattr(main,'model',object())
    source=urdu_segment()
    segment=SimpleNamespace(start=0,end=3,text=source['text'],words=[SimpleNamespace(**w) for w in source['words']])
    seen=[]
    def recognize(*args,**options):
        seen.append(options)
        return iter([segment]),SimpleNamespace(language='ur')
    monkeypatch.setattr(speech,'transcribe',recognize)
    response=client.post('/api/projects/roman-test/transcribe',json={'redo':True,'caption_script':'roman_urdu','speech_language':'ur'})
    assert response.status_code==202 and len(calls)==1
    main.process('roman-test')
    p=store.get('roman-test')
    assert p['status']=='ready' and p['transcript'][0]['text']=='main theek hoon.'
    assert p['source_transcript'][0]['text']==source['text']
    assert seen==[{'language':'ur','caption_script':'roman_urdu'}] and len(p['clips'])==1


def test_language_options_validate_for_upload_and_import():
    assert main.LinkImportInput(url='https://example.com/video.mp4',caption_script='roman_urdu',speech_language='hi').speech_language=='hi'
    with pytest.raises(ValueError):main.GenerationInput(speech_language='Roman')


@pytest.mark.parametrize('mode',['fast','balanced','accurate'])
def test_speech_language_hint_reaches_whisper(monkeypatch,mode):
    import sys
    calls=[]
    class Recognizer:
        def transcribe(self,source,**options):calls.append(options)
    class Pipeline(Recognizer):
        def __init__(self,model):pass
    monkeypatch.setitem(sys.modules,'faster_whisper',SimpleNamespace(BatchedInferencePipeline=Pipeline))
    speech.transcribe(Recognizer(),'source',mode,language='hi')
    assert calls[0]['language']=='hi' and calls[0]['word_timestamps'] is True
