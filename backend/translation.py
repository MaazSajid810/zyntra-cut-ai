"""Local Argos/OpenNMT models, CTranslate2 CPU int8, sentence timing only.

Model installation is an explicit setup script, never a request-time arbitrary URL.
No transcript is sent to an external translation service.
"""
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from .languages import CAPTION_TARGETS
import json
import os
import re

ROOT=Path(os.environ.get('CLIPFORGE_TRANSLATION_MODELS',Path(__file__).resolve().parents[1]/'data'/'translations'))
PAIRS={('en','ur'):'1_9',('ur','en'):'1_9',('en','hi'):'1_1',('hi','en'):'1_1',
       ('en','es'):'1_0',('es','en'):'1_9',('en','fr'):'1_9',('fr','en'):'1_9',
       ('en','de'):'1_3',('de','en'):'1_3',('en','it'):'1_0',('it','en'):'1_0',
       ('en','pt'):'1_9',('pt','en'):'1_9',('en','ar'):'1_0',('ar','en'):'1_0',
       ('en','bn'):'1_9',('bn','en'):'1_9'}
CORE_LANGUAGES={'en','ur','hi'}


def pair_installed(source,target):
    folder=ROOT/f'{source}_{target}'
    return all((folder/name).is_file() for name in ('model/model.bin','metadata.json','sentencepiece.model'))


def route(source,target):
    if source==target:return []
    if (source,target) in PAIRS:return [(source,target)]
    if source!='en' and target!='en' and (source,'en') in PAIRS and ('en',target) in PAIRS:
        return [(source,'en'),('en',target)]
    return None


def route_available(source,target):
    steps=route(source,target)
    return steps is not None and all(pair_installed(*pair) for pair in steps)


def conversion_available(source,script):
    target=CAPTION_TARGETS.get(script)
    return (script=='original' or source==target or
            (script=='roman_urdu' and source in ('ur','hi')) or
            route_available(source,target))


@lru_cache(maxsize=2)
def engine(source,target):
    import ctranslate2
    import sentencepiece
    folder=ROOT/f'{source}_{target}'
    if not (folder/'model'/'model.bin').exists():
        raise ValueError('Translation model is missing. Run python -m scripts.setup_translation, then retry. Your source and transcript are kept.')
    metadata=json.loads((folder/'metadata.json').read_text(encoding='utf-8'))
    tokenizer=sentencepiece.SentencePieceProcessor(model_file=str(folder/'sentencepiece.model'))
    translator=ctranslate2.Translator(str(folder/'model'),device='cpu',compute_type='int8',inter_threads=1,intra_threads=max(1,min(4,os.cpu_count() or 1)))
    return translator,tokenizer,metadata.get('target_prefix','')


def translate_texts(texts,source,target):
    if source==target:return list(texts)
    steps=route(source,target)
    if steps is None:
        raise ValueError('No local translation route is available for these languages. Use Original captions to preserve the recognized speech.')
    if len(steps)>1:
        return translate_texts(translate_texts(texts,source,'en'),'en',target)
    translator,tokenizer,prefix=engine(source,target)
    # Bound each model input without guessing new subtitle timestamps.
    pieces=[];owners=[]
    for index,text in enumerate(texts):
        chunks=re.findall(r'.{1,350}(?:\s+|$)|\S{1,350}',text.strip()) or ['']
        for chunk in chunks:
            pieces.append(tokenizer.encode(chunk.strip(),out_type=str));owners.append(index)
    results=translator.translate_batch(pieces,target_prefix=[[prefix]]*len(pieces) if prefix else None,
        beam_size=4,max_batch_size=256,batch_type='tokens',replace_unknowns=True,max_decoding_length=512)
    output=['' for _ in texts]
    for owner,result in zip(owners,results):
        text=tokenizer.decode(result.hypotheses[0]).replace('\u2581',' ').replace('_',' ').strip()
        if prefix and text.startswith(prefix):text=text[len(prefix):].strip()
        output[owner]+=(' ' if output[owner] else '')+text
    if any(original.strip() and not translated.strip() for original,translated in zip(texts,output)):
        raise ValueError('Translation produced an empty sentence. Review the source transcript and retry.')
    return output


def convert_segments(segments,source,script):
    from . import romanization
    target=CAPTION_TARGETS.get(script)
    if not target:return deepcopy(segments)
    # Urdu and Hindi share speech: preserve the recognized words for Roman output.
    if script=='roman_urdu' and source in ('ur','hi'):
        return romanization.convert_segments(segments,script)
    if source==target:return deepcopy(segments)
    translated=translate_texts([s['text'] for s in segments],source,target)
    result=[]
    for segment,text in zip(segments,translated):
        item={**segment,'text':romanization.roman_text(text) if script=='roman_urdu' else text,'timing':'translated_sentence','source_text':segment['text']}
        negative={
            'en':r"\b(not|never|no|cannot|can't|don't|doesn't|didn't|won't|isn't|aren't)\b",
            'ur':r'(نہیں|نہ|مت)', 'hi':r'(नहीं|मत|\bन\b)',
        }
        if source in negative and target in negative and re.search(negative[source],segment['text'],re.I) and not re.search(negative[target],text,re.I):
            item['translation_warning']='Review meaning: the source contains a negative statement which may be missing in this translation.'
        item.pop('words',None)  # Reordered words cannot inherit source word times.
        result.append(item)
    return result
