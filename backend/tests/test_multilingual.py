from types import SimpleNamespace
import re
import pytest
from backend import multilingual,translation


def test_m2m_language_tokens_and_sentence_boundaries_do_not_change_caption_ownership(monkeypatch,tmp_path):
    calls=[]
    tokenizer=SimpleNamespace(encode=lambda text,out_type:[text],decode=lambda tokens:' '.join(tokens))
    def translate(tokens,**kwargs):
        calls.append((tokens,kwargs))
        return [SimpleNamespace(hypotheses=[[kwargs['target_prefix'][i][0],f'result{i}','</s>']]) for i in range(len(tokens))]
    monkeypatch.setattr(multilingual,'engine',lambda path:(SimpleNamespace(translate_batch=translate),tokenizer))
    output=multilingual.translate(['First sentence. Second sentence.','Another subtitle.'],'en','ur',tmp_path)
    assert output==['result0 result1','result2']
    assert calls[0][0]==[['__en__','First sentence.'],['__en__','Second sentence.'],['__en__','Another subtitle.']]
    assert calls[0][1]['target_prefix']==[['__ur__']]*3


@pytest.mark.parametrize('target,negative',[('ur',r'نہ|نہیں'),('hi',r'न |नहीं')])
def test_real_multilingual_translation_keeps_simple_negative_and_positive_meanings(target,negative):
    if not multilingual.installed(translation.ROOT):pytest.skip('Optional multilingual model is not installed')
    translated=translation.translate_texts(['Do not open the door.','You must open the door.'],'en',target)
    assert re.search(negative,translated[0]),translated
    assert not re.search(negative,translated[1]),translated
    assert translated[0]!=translated[1]
