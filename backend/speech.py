"""CPU speech recognition with bounded batching and independent window decoding."""
import os
from functools import lru_cache
import re
import unicodedata
from contextlib import contextmanager
import tempfile
from pathlib import Path
from collections import Counter


def validate_text(text):
    tokens=text.casefold().split()
    compact=re.sub(r'\s+','',unicodedata.normalize('NFC',text.casefold()))
    # Some failed multilingual decodes repeat syllables/combining marks inside
    # a single token. A whitespace word counter cannot detect those loops.
    loop=any(len(match.group())>=32 for match in re.finditer(r'(.{1,12}?)\1{7,}',compact))
    if loop or text.count('\ufffd')>=3 or len(tokens)>=32 and Counter(tokens).most_common(1)[0][1]/len(tokens)>.65:
        raise ValueError('Speech recognition produced repeated or unreadable words instead of reliable captions. '
                         'Choose the actual Spoken language and re-transcribe in Quick or Balanced mode. Your previous transcript is kept.')


@contextmanager
def timeline_audio(source):
    """Whisper discards frame PTS. Fill timestamp gaps before decoding speech."""
    from . import media
    with tempfile.TemporaryDirectory(prefix='zyntra-speech-') as temporary:
        audio=Path(temporary)/'timeline.wav'
        media.run(['-i',str(source),'-map','0:a:0','-vn','-sn','-dn',
                   '-af','aresample=16000:async=1:first_pts=0','-ac','1','-ar','16000','-c:a','pcm_s16le',str(audio)])
        yield audio


@lru_cache(maxsize=4)
def hindi_suppressed_tokens(tokenizer):
    # Whisper uses GPT-2 byte symbols. Suppress Arabic UTF-8 leading bytes as
    # well as whole Arabic-script tokens so split-byte tokens cannot bypass it.
    return tuple(token for piece,token in tokenizer.get_vocab().items()
                 if any(byte in piece for byte in 'ØÙÚÛ') or re.search(r'[\u0600-\u06ff]',tokenizer.decode([token])))


def fast_batch_size():
    try:
        return max(1,min(8,int(os.environ.get('CLIPFORGE_FAST_BATCH_SIZE','4'))))
    except ValueError:
        return 4


def model_name(mode,script='original',language='auto'):
    # A translated output must not choose the speech model or decoding language.
    if script not in ('original','roman_urdu') and language in ('auto','ur','hi'):
        return os.environ.get('WHISPER_HINDI_MODEL','small')
    if language in ('ur','hi','pa','ps','sd'):return os.environ.get('WHISPER_HINDI_MODEL','small')
    if script=='roman_urdu' and language!='en':return os.environ.get('WHISPER_ROMAN_MODEL','small')
    return 'tiny' if mode=='fast' else os.environ.get('WHISPER_MODEL','base')


def load_model(name,cache):
    from faster_whisper import WhisperModel
    from huggingface_hub.errors import LocalEntryNotFoundError
    settings={'device':'cpu','compute_type':'int8','download_root':str(cache)}
    try:
        return WhisperModel(name,local_files_only=True,**settings)
    except (LocalEntryNotFoundError,FileNotFoundError):
        return WhisperModel(name,**settings)


def detect_language(recognizer, source):
    if not hasattr(recognizer,'detect_language'):
        return None
    import wave
    import numpy as np
    with wave.open(str(source),'rb') as audio:
        if audio.getsampwidth()!=2 or audio.getnchannels()!=1 or audio.getframerate()!=16000:
            return None
        samples=np.frombuffer(audio.readframes(16000*90),dtype='<i2').astype(np.float32)/32768
    detected,confidence,_=recognizer.detect_language(audio=samples,vad_filter=True,language_detection_segments=3)
    return detected,confidence


def resolve_language(recognizer,source,requested):
    """Prevent a subtitle target accidentally forcing unrelated source speech."""
    result=detect_language(recognizer,source)
    if not result:return (None if requested in (None,'auto') else requested),None
    detected,confidence=result
    if requested in (None,'auto'):
        return (detected if confidence>=.8 else None),None
    if detected==requested or {detected,requested}=={'ur','hi'} or confidence<.8:
        return requested,None
    from .languages import SPEECH_NAMES
    detail=f"Audio detection found {SPEECH_NAMES.get(detected,detected)} ({confidence:.0%}), while source speech was set to {SPEECH_NAMES.get(requested,requested)}."
    if confidence<.95:
        raise ValueError(detail+' Choose Detect & repair captions to avoid decoding in the wrong language. Your previous transcript is kept.')
    return detected,detail+' Captions were recognized from the detected speech; the subtitle output language is applied separately.'


def check_language(recognizer, source, requested):
    """Compatibility diagnostic; processing uses resolve_language before decoding."""
    if requested in (None,'auto'):return None
    result=detect_language(recognizer,source)
    if not result:return None
    detected,confidence=result
    if confidence>=.8 and detected!=requested and {detected,requested}!={'ur','hi'}:
        from .languages import SPEECH_NAMES
        return (f'Source language is set to {SPEECH_NAMES.get(requested,requested)}, but an independent audio sample detected '
                f'{SPEECH_NAMES.get(detected,detected)} ({confidence:.0%} confidence). The selected source language was respected. '
                'Use Detect & repair captions to recognize the actual speech again; changing subtitle output alone cannot fix misheard words.')
    return None


def transcribe(recognizer, source, mode, language=None, caption_script='original'):
    options = {'task':'transcribe',**({'language': language} if language else {})}
    def script_options(code):
        result={'task':'transcribe','language':code}
        # A real Hindi-script speech pass, not a guessed Roman-to-Hindi mapping.
        # Hindi/Urdu share speech, but small models may otherwise emit Urdu script.
        if code=='hi':result.update(suppress_tokens=[-1,*hindi_suppressed_tokens(recognizer.hf_tokenizer)])
        return result
    target={'hindi':'hi','urdu':'ur'}.get(caption_script)
    if target and language in ('ur','hi'):
        options=script_options(target)
    def decode(settings):
        detection={'language_detection_segments':3,'language_detection_threshold':.8} if not settings.get('language') else {}
        # Batched decoding collapsed real Urdu dialogue into one repeated late
        # segment. Independent decoding preserves these languages and timings.
        if mode in ('fast','quick') and settings.get('language') not in ('ur','hi','pa','ps','sd'):
            from faster_whisper import BatchedInferencePipeline
            return BatchedInferencePipeline(model=recognizer).transcribe(
                str(source),batch_size=fast_batch_size(),beam_size=1,temperature=0,
                vad_filter=True,vad_parameters={'min_silence_duration_ms':500},
                without_timestamps=False,word_timestamps=True,**detection,**settings)
        # An intro/music hallucination must not become the prompt for the rest
        # of a long source. Independent windows also stop cross-window loops.
        return recognizer.transcribe(str(source),beam_size=5 if mode=='accurate' else 1,temperature=0,vad_filter=True,word_timestamps=True,
                                     condition_on_previous_text=False,**detection,**settings)
    # Roman output is produced from the actual native transcript afterwards.
    # Instructions in initial_prompt can be copied/hallucinated as speech.
    result=decode(options)
    # Inspect language detection before forcing a script. English must remain
    # English here, then use a translation model rather than mishear it as Hindi.
    if target and not language and result[1].language in ('ur','hi') and result[1].language!=target:
        return decode(script_options(target))
    return result
