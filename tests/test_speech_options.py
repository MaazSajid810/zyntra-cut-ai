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
