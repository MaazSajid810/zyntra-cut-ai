"""Local M2M100 INT8 translation, using the documented Fairseq language tokens."""
from functools import lru_cache
import os
import re

LANGUAGES=frozenset('af am ar ast az ba be bg bn br bs ca ceb cs cy da de el en es et fa ff fi fr fy ga gd gl gu ha he hi hr ht hu hy id ig ilo is it ja jv ka kk km kn ko lb lg ln lo lt lv mg mk ml mn mr ms my ne nl no ns oc or pa pl ps pt ro ru sd si sk sl so sq sr ss su sv sw ta th tl tn tr uk ur uz vi wo xh yi yo zh zu'.split())


def installed(root):
    return all((root/'m2m100'/name).is_file() for name in ('model.bin','config.json','shared_vocabulary.txt','spm.128k.model'))


@lru_cache(maxsize=1)
def engine(folder):
    import ctranslate2
    import sentencepiece
    translator=ctranslate2.Translator(folder,device='cpu',compute_type='int8',inter_threads=1,intra_threads=max(1,min(4,os.cpu_count() or 1)))
    tokenizer=sentencepiece.SentencePieceProcessor(model_file=folder+'/spm.128k.model')
    return translator,tokenizer


def translate(texts,source,target,root,progress=None):
    translator,tokenizer=engine(str(root/'m2m100'))
    pieces=[];owners=[]
    for owner,text in enumerate(texts):
        # Sentence punctuation remains part of the input. Bound long subtitle
        # paragraphs to the model's trained context without guessing word times.
        sentences=re.split(r'(?<=[.!?۔؟।;])\s+',text.strip())
        for sentence in sentences:
            for chunk in re.findall(r'.{1,350}(?:\s+|$)|\S{1,350}',sentence) or ['']:
                pieces.append([f'__{source}__',*tokenizer.encode(chunk.strip(),out_type=str)])
                owners.append(owner)
    results=[]
    for start in range(0,len(pieces),24):
        batch=pieces[start:start+24]
        results.extend(translator.translate_batch(batch,target_prefix=[[f'__{target}__'] for _ in batch],
            beam_size=5,max_batch_size=128,batch_type='tokens',max_decoding_length=256,
            repetition_penalty=1.1,no_repeat_ngram_size=3))
        if progress:progress(min(start+24,len(pieces)),len(pieces))
    outputs=['' for _ in texts]
    for owner,result in zip(owners,results):
        tokens=[token for token in result.hypotheses[0] if not token.startswith('__') and token not in ('</s>','<s>','<pad>')]
        output=tokenizer.decode(tokens).strip()
        outputs[owner]+=(' ' if outputs[owner] else '')+output
    if any(text.strip() and not output for text,output in zip(texts,outputs)):
        raise ValueError('Local translation produced an empty sentence. Your previous captions are kept.')
    return outputs
