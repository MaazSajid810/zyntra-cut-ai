from types import SimpleNamespace
import sys

import pytest
from backend import speech


@pytest.mark.parametrize('value,expected',[('1',1),('4',4),('100',8),('0',1),('oops',4)])
def test_fast_batch_memory_limit(monkeypatch,value,expected):
    monkeypatch.setenv('CLIPFORGE_FAST_BATCH_SIZE',value)
    assert speech.fast_batch_size()==expected


@pytest.mark.parametrize('mode',['fast','quick'])
def test_fast_batched_recognition_keeps_timestamps(monkeypatch,mode):
    calls=[]
    recognizer=object()
    class Pipeline:
        def __init__(self,model):assert model is recognizer
        def transcribe(self,source,**options):
            calls.append((source,options))
            return iter(()),SimpleNamespace(language='en')
    monkeypatch.setitem(sys.modules,'faster_whisper',SimpleNamespace(BatchedInferencePipeline=Pipeline))
    monkeypatch.setenv('CLIPFORGE_FAST_BATCH_SIZE','4')
    speech.transcribe(recognizer,'source.mp4',mode)
    options=calls[0][1]
    assert options['batch_size']==4 and options['beam_size']==1
    assert options['temperature']==0 and options['without_timestamps'] is False
    assert options['vad_filter'] is True
    assert options['word_timestamps'] is True
    assert options['language_detection_segments']==3 and options['language_detection_threshold']==.8


def test_quick_mode_keeps_balanced_model_instead_of_tiny(monkeypatch):
    monkeypatch.delenv('WHISPER_MODEL',raising=False)
    monkeypatch.delenv('WHISPER_HINDI_MODEL',raising=False)
    assert speech.model_name('quick','original','en')==speech.model_name('balanced','original','en')=='base'
    assert speech.model_name('quick','roman_urdu','ur')==speech.model_name('balanced','roman_urdu','ur')
    assert speech.model_name('quick','original','pa')==speech.model_name('balanced','original','pa')=='small'


@pytest.mark.parametrize('mode,beam',[('balanced',1),('accurate',5)])
def test_other_modes_reset_context_to_avoid_long_video_hallucination_loops(mode,beam):
    calls=[]
    recognizer=SimpleNamespace(transcribe=lambda source,**options:calls.append(options))
    speech.transcribe(recognizer,'source.mp4',mode)
    assert calls==[{'beam_size':beam,'temperature':0,'vad_filter':True,'word_timestamps':True,'task':'transcribe',
                   'condition_on_previous_text':False,'language_detection_segments':3,'language_detection_threshold':.8}]


def test_cached_model_load_does_not_contact_network(monkeypatch,tmp_path):
    calls=[]
    def load(name,**options):calls.append(options);return object()
    monkeypatch.setitem(sys.modules,'faster_whisper',SimpleNamespace(WhisperModel=load))
    speech.load_model('small',tmp_path)
    assert len(calls)==1 and calls[0]['local_files_only'] is True


def test_forced_wrong_source_language_is_detected_without_silently_overriding(tmp_path):
    import wave
    path=tmp_path/'timeline.wav'
    with wave.open(str(path),'wb') as audio:
        audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(16000);audio.writeframes(b'\0'*32000)
    recognizer=SimpleNamespace(detect_language=lambda **kwargs:('ur',.91,[]))
    warning=speech.check_language(recognizer,path,'en')
    assert 'English' in warning and 'Urdu' in warning and 'Detect & repair' in warning
    assert speech.check_language(recognizer,path,'auto') is None
    assert speech.check_language(recognizer,path,'hi') is None  # Shared spoken language/script choice.
    recognizer.detect_language=lambda **kwargs:('es',.55,[])
    assert speech.check_language(recognizer,path,'en') is None


def test_hallucination_loop_is_not_presented_as_recognized_speech():
    with pytest.raises(ValueError,match='actual Spoken language'):
        speech.validate_text('hello '*50)
    with pytest.raises(ValueError,match='unreadable'):
        speech.validate_text('\ufffd \ufffd \ufffd')
    speech.validate_text('No, no. Please listen to what I am saying.')


@pytest.mark.parametrize('text',['GTA 6 '+chr(0x0c32)+chr(0x0c4d)*60,'నిని'*50,'hello'*12])
def test_repeated_syllables_and_combining_marks_inside_one_token_are_rejected(text):
    with pytest.raises(ValueError,match='repeated or unreadable'):speech.validate_text(text)


def test_output_language_does_not_force_english_into_multilingual_model():
    assert speech.model_name('quick','punjabi','en')==speech.model_name('quick','original','en')
    assert speech.model_name('quick','urdu','en')==speech.model_name('quick','original','en')


@pytest.mark.parametrize('language',['ur','hi','pa','ps','sd'])
def test_regional_quick_speech_uses_independent_decoder_with_word_times(language):
    calls=[]
    recognizer=SimpleNamespace(transcribe=lambda source,**kwargs:calls.append(kwargs))
    speech.transcribe(recognizer,'source.wav','quick',language=language)
    assert calls[0]['language']==language and calls[0]['beam_size']==1
    assert calls[0]['word_timestamps'] and not calls[0]['condition_on_previous_text']


def test_confident_wrong_source_is_corrected_before_asr_and_uncertain_mismatch_preserves_transcript(monkeypatch):
    monkeypatch.setattr(speech,'detect_language',lambda *args:('en',.99))
    actual,warning=speech.resolve_language(object(),'audio.wav','pa')
    assert actual=='en' and 'Punjabi' in warning and 'English' in warning
    assert speech.resolve_language(object(),'audio.wav','auto')==('en',None)
    monkeypatch.setattr(speech,'detect_language',lambda *args:('ur',.86))
    with pytest.raises(ValueError,match='previous transcript is kept'):
        speech.resolve_language(object(),'audio.wav','en')
    assert speech.resolve_language(object(),'audio.wav','hi')==('hi',None)
