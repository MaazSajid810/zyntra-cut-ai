"""Local Urdu/Hindi script conversion, never translation or fabricated ASR timing."""
from copy import deepcopy
from functools import lru_cache
import re

from .captions import aligned

URDU = re.compile(r'[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff\ufb50-\ufdff\ufe70-\ufeff]+')
HINDI = re.compile(r'[\u0900-\u097f]+')
HINDI_SPELLINGS = {'मैं':'main','में':'mein','हैं':'hain','है':'hai','हूँ':'hoon','हूं':'hoon',
                  'नहीं':'nahin','यहाँ':'yahan','यहां':'yahan','वहाँ':'wahan','वहां':'wahan',
                  'क्यों':'kyun','ठीक':'theek','वीडियो':'video','नई':'nayi'}


@lru_cache(maxsize=1)
def hindi_engine():
    from uroman import Uroman
    return Uroman()


def hindi_word(match):
    word=match.group()
    if word in HINDI_SPELLINGS:
        return HINDI_SPELLINGS[word]
    # Use informal Latin vowels rather than uroman's doubled retroflex spelling.
    text=hindi_engine().romanize_string(word,lcode='hin')
    return text.replace('tth','th').replace('dd','d').replace('ii','ee').replace('uu','oo')


@lru_cache(maxsize=8192)
def roman_text(text):
    # Convert only the source-script runs. Latin names, English and punctuation
    # retain their original spelling/case, including code-switched speech.
    text=text.translate(str.maketrans({'،': ',', '۔': '.', '؟': '?', '।': '.', '॥': '.'}))
    if URDU.search(text):
        from urdunlp import transliterate_to_roman
        text = URDU.sub(lambda m: transliterate_to_roman(m.group()), text)
    if HINDI.search(text):
        text = HINDI.sub(hindi_word, text)
    return text


def convert_segments(segments, script):
    result = deepcopy(segments)
    if script == 'original':
        return result
    if script in ('hindi','urdu','english'):
        if script!='hindi':return result
        if any(URDU.search(s['text']) for s in result):
            raise ValueError('Hindi script needs a fresh Hindi audio transcription.')
        return result
    if script != 'roman_urdu':
        raise ValueError('Unsupported subtitle script')
    for segment in result:
        was_aligned = aligned(segment)
        segment['text'] = roman_text(segment['text'])
        if was_aligned:
            for word in segment['words']:
                word['word'] = roman_text(word['word'])
            segment['text'] = ' '.join(w['word'].strip() for w in segment['words']).strip()
        else:
            segment.pop('words', None)
    return result
