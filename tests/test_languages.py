"""Language choices must match recognition tokens and installed local routes."""
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend import guest, languages, main, speech, store, translation
from scripts import setup_translation


def segment(text):
    return {'id':0,'start':1.25,'end':4.5,'text':text,
            'words':[{'word':text,'start':1.25,'end':4.5}]}


@pytest.fixture
def workspace(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DATA',tmp_path/'projects')
    store.DATA.mkdir()
    monkeypatch.setattr(translation,'ROOT',tmp_path/'translations')
    translation.engine.cache_clear()
    with TestClient(main.app) as client:
        client.get('/api/session')
        source=[segment('Hola, buenos dias.')]
        project={'id':'languages','owner_id':guest.owner_for_token(client.cookies.get(guest.COOKIE)),
                 'status':'ready','has_audio':True,'duration':8,'language':'es',
                 'caption_script':'original','source_transcript':source,'transcript':deepcopy(source),
                 'clips':[{'id':'kept','start':0,'end':8,'title':'Kept','score':80,
                           'status':'ready','file':'kept.mp4'}]}
        store.save(project)
        yield client,project
    translation.engine.cache_clear()


def install_fixture(source,target):
    folder=translation.ROOT/f'{source}_{target}'
    (folder/'model').mkdir(parents=True)
    for name in ('model/model.bin','metadata.json','sentencepiece.model'):
        (folder/name).write_bytes(b'Unit test sentinel; not a usable translation model')


def test_recognition_catalog_matches_actual_runtime_tokens():
    from faster_whisper.tokenizer import _LANGUAGE_CODES
    assert set(languages.SPEECH_NAMES)==set(_LANGUAGE_CODES)


@pytest.mark.parametrize('code',['hi','pa','ps','sd','es','fr','ar','bn','de','pt','it','ja','zh'])
def test_generation_accepts_real_source_tokens(code):
    assert main.GenerationInput(speech_language=code).speech_language==code
    assert main.LinkImportInput(url='https://example.com/video.mp4',speech_language=code).speech_language==code


def test_invalid_source_and_target_choices_rejected():
    with pytest.raises(ValidationError):main.GenerationInput(speech_language='made_up')
    with pytest.raises(ValidationError):main.TranscriptScriptInput(caption_script='made_up')


@pytest.mark.parametrize('script,text',[
    ('punjabi','ਸਤ ਸ੍ਰੀ ਅਕਾਲ'),('pashto','ستاسو نوم څه دی؟'),('sindhi','توهان جو نالو ڇا آهي؟'),
    ('spanish','Hola, buenos dias.'),('french','Bonjour à tous.'),('arabic','مرحبا بكم'),
    ('bengali','আপনার নাম কি?'),('german','Guten Tag.'),('portuguese','Bom dia.'),('italian','Buongiorno.'),
])
def test_native_caption_choice_preserves_words_and_timestamps(script,text,monkeypatch):
    original=[segment(text)]
    def no_translation(*args):pytest.fail('Same-language captions must not call a translator or transliterator.')
    monkeypatch.setattr(translation,'translate_texts',no_translation)
    result=translation.convert_segments(original,languages.CAPTION_TARGETS[script],script)
    assert result==original and result is not original and result[0]['words'] is not original[0]['words']


def test_caption_capabilities_require_a_private_guest_and_report_installed_pairs(workspace):
    client,_=workspace
    unauthenticated=TestClient(main.app)
    assert unauthenticated.get('/api/languages').status_code==401
    install_fixture('en','es')
    response=client.get('/api/languages')
    assert response.status_code==200 and response.headers['cache-control']=='private, no-store'
    body=response.json()
    assert len(body['speech_languages'])==101
    choices={entry['script']:entry for entry in body['caption_languages']}
    assert choices['spanish']['translation_available'] is True
    assert choices['punjabi']['language']=='pa' and choices['punjabi']['translation_available'] is False
    assert any(pair=={'source':'en','target':'es','installed':True} for pair in body['translation_pairs'])
    assert not any(pair['installed'] for pair in body['translation_pairs'] if pair['source']=='es')


def test_route_requires_both_installed_hops(workspace):
    install_fixture('es','en')
    assert translation.route_available('es','es')
    assert translation.route('es','ur')==[('es','en'),('en','ur')]
    assert not translation.route_available('es','ur')
    install_fixture('en','ur')
    assert translation.route_available('es','ur')
    assert not translation.route_available('es','pa')


def test_missing_new_route_keeps_native_speech_and_requested_target(workspace,monkeypatch):
    client,project=workspace
    def no_recognition(*args):pytest.fail('Changing caption language must reuse saved speech.')
    monkeypatch.setattr(main.pool,'submit',no_recognition)
    response=client.post('/api/projects/languages/transcript/script',json={'caption_script':'punjabi'})
    assert response.status_code==200
    body=response.json()
    assert body['transcript']==project['source_transcript'] and body['source_transcript']==project['source_transcript']
    assert body['caption_script']=='original' and body['requested_caption_script']=='punjabi'
    assert 'Punjabi' in body['caption_warning'] and 'original-language' in body['caption_warning']
    assert body['clips']==project['clips']


def test_new_native_language_applies_without_asr_or_translation(workspace,monkeypatch):
    client,project=workspace
    monkeypatch.setattr(main.pool,'submit',lambda *args:pytest.fail('No repeat ASR'))
    response=client.post('/api/projects/languages/transcript/script',json={'caption_script':'spanish'})
    assert response.status_code==200
    body=response.json()
    assert body['caption_script']=='spanish' and body['transcript']==project['source_transcript']
    assert body['caption_warning'] is None and body['clips']==project['clips']


def test_installed_caption_translation_reuses_saved_speech_and_drops_false_word_times(workspace,monkeypatch):
    client,project=workspace
    install_fixture('es','en')
    calls=[]
    monkeypatch.setattr(main.pool,'submit',lambda *args:pytest.fail('No repeat ASR'))
    def translated(texts,source,target):calls.append((texts,source,target));return ['Hello, good morning.']
    monkeypatch.setattr(translation,'translate_texts',translated)
    response=client.post('/api/projects/languages/transcript/script',json={'caption_script':'english'})
    assert response.status_code==200
    body=response.json();converted=body['transcript'][0]
    assert calls==[(['Hola, buenos dias.'],'es','en')]
    assert converted['text']=='Hello, good morning.' and converted['timing']=='translated_sentence'
    assert (converted['start'],converted['end'])==(1.25,4.5) and 'words' not in converted
    assert body['source_transcript']==project['source_transcript']
    assert body['clips'][0]['status']=='draft' and body['clips'][0]['file'] is None
    assert (body['clips'][0]['start'],body['clips'][0]['end'])==(0,8)
    restored=client.post('/api/projects/languages/transcript/script',json={'caption_script':'original'}).json()
    assert restored['transcript']==project['source_transcript']


def test_setup_default_keeps_existing_models_and_spanish_is_explicit():
    assert setup_translation.selected_pairs([])==[('en','ur'),('ur','en'),('en','hi'),('hi','en')]
    assert setup_translation.selected_pairs(['--languages','es'])==[('en','es'),('es','en')]
    assert setup_translation.selected_pairs(['--pairs','en:es'])==[('en','es')]
    with pytest.raises(SystemExit):setup_translation.selected_pairs(['--languages','pa'])


@pytest.mark.parametrize('language',['pa','ps','sd'])
def test_regional_speech_uses_existing_small_model(language):
    assert speech.model_name('balanced','original',language)=='small'
