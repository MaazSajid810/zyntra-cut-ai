"""Grounded, inspectable transcript selection. Scores are heuristics, not view predictions."""
import hashlib
import re


def words(text):
    # Hindi vowel signs are combining marks: plain \w splits words such as क्यों.
    return re.findall(r"[\w\u0900-\u0903\u093a-\u094f\u0951-\u0957\u0962-\u0963']+", text.lower().replace('ي','ی').replace('ك','ک'))


HOOKS={'why','how','secret','mistake','imagine','unexpected','surprising','discovered',
       'cómo','como','qué','secreto','error','truco','sorpresa','increíble','descubrí',
       'kyun','kyon','kaise','kaisa','galti','ghalti','raaz',
       'क्यों','कैसे','गलती','रहस्य','हैरान','راز','کیوں','کیسے','غلطی','حیران'}
PAYOFFS={'because','therefore','finally','result','solution','lesson','instead','solved','learned','discovered',
         'porque','resultado','solución','solucion','finalmente','entonces','aprendí','aprendi','conseguí','descubrí',
         'isliye','islie','akhir','aakhir','seekha','lekin','wajah','nateeja',
         'क्योंकि','इसलिए','आखिर','नतीजा','समाधान','सीखा','लेकिन',
         'کیونکہ','نتیجہ','آخر','سبق','لیکن','وجہ','حل'}
ENDINGS=('.', '!', '۔', '！', '।', '॥')


def signature(text):
    tokens=words(text)
    return sorted({hashlib.sha256(' '.join(tokens[i:i+4]).encode()).hexdigest()[:16] for i in range(max(0,len(tokens)-3))})[:256]


def repeated(a,b):
    a,b=set(a),set(b)
    return bool(a and b) and len(a&b)/min(len(a),len(b))>=.72


def assess(items,start,end,measurements=None):
    text=' '.join(s['text'].strip() for s in items).strip()
    tokens=words(text)
    opening=' '.join(words(items[0]['text'])[:20])
    opening_words=set(words(opening))
    hook_matches=opening_words&HOOKS
    question=any(mark in items[0]['text'] for mark in ('?','؟'))
    hook=min(100,20+35*bool(hook_matches)+25*question+20*bool(re.search(r'\b(nobody|never|stop|don.t|what if|here.s|did you|kya|kabhi)\b',opening)))
    payoff_matches=set(tokens)&PAYOFFS
    normalized=' '.join(tokens)
    for phrase in ('is liye','is lie','is liay','is lye','اس لیے','اس لئے','इस लिए'):
        if phrase in normalized:payoff_matches.add(phrase)
    closing=items[-1]['text'].strip()
    complete=closing.endswith(ENDINGS)
    dependent=bool(re.match(r'^(and|but|so|then|he|she|they|it|also|aur|phir)\b',opening))
    completeness=max(0,35+45*complete+20*bool(payoff_matches)-30*dependent)
    payoff=min(100,20+40*bool(payoff_matches)+20*bool(re.search(r'\b\d+\b',text))+20*bool(set(tokens)&{'you','your','aap','tum'}))
    covered=sum(max(0,min(end,s['end'])-max(start,s['start'])) for s in items if s['text'].strip())
    coverage=min(1,covered/max(1,end-start))
    rate=len(tokens)/max(1,end-start)
    pacing=round(100*coverage*min(1,rate/1.5)*(1 if rate<=4.5 else .6))
    unique=len(set(tokens))/max(1,len(tokens))
    specificity=min(100,20+40*bool(payoff_matches)+25*bool(re.search(r'\d',text))+15*bool(hook_matches))
    factors={'opening_hook':hook,'complete_thought':completeness,'payoff_or_value':payoff,'speech_pacing':pacing,'specificity':specificity}
    score=round(hook*.30+completeness*.25+payoff*.20+pacing*.15+specificity*.10)
    if unique<.35:score=min(score,35)
    if not complete:score=min(score,59)
    if not payoff_matches:score=min(score,64)
    if not hook_matches and not question:score=min(score,64)
    reasons=[]
    if hook_matches:reasons.append('Opening hook: '+', '.join(sorted(hook_matches)))
    if question:reasons.append('Opening question')
    if payoff_matches:reasons.append('Explanation/payoff markers: '+', '.join(sorted(payoff_matches)))
    if complete:reasons.append('Ends at a sentence boundary')
    recommendations=[]
    if dependent:recommendations.append('Review the opening: it may depend on earlier context.')
    if not payoff_matches:recommendations.append('Review whether the clip delivers a clear payoff.')
    if coverage<.8:recommendations.append('Check pauses before publishing.')
    evidence={'method':'transcript-heuristic-v2','factors':factors,'opening_excerpt':items[0]['text'][:240],
            'speech_coverage':round(coverage,3),'recommendations':recommendations,
            'limitations':'Transcript signals only. No visual/emotion analysis or calibrated view prediction.'}
    if measurements:
        from .analysis import interval_evidence
        measured=interval_evidence(measurements,start,end)
        additions={k:v for k,v in measured.items() if k in ('audio_energy','visual_activity') and v is not None}
        # These are conservative supporting signals; loudness/scene cuts cannot
        # promote an incomplete or weak transcript above its linguistic ceiling.
        if additions:
            combined=round(score*.85+sum(additions.values())/len(additions)*.15)
            score=min(score,combined) if score<65 else combined
        score=max(0,score-round(measured['silence_fraction']*25))
        factors.update(additions)
        evidence.update(method='transcript-heuristic-v3+measured-media',measurements=measured,
                        limitations=measurements['limitations'])
        if measured['silence_fraction']>.2:recommendations.append('Measured silence exceeds 20%; review pacing.')
    return {'start':round(start,3),'end':round(end,3),'title':' '.join(text.split()[:9]),'score':score,
        'reason':' · '.join(reasons) or 'Limited transcript engagement signals',
        'selection_evidence':evidence,
        'content_signature':signature(text)}


def highlights(segments,duration,limit=5,exclude=(),minimum_score=70,measurements=None,min_duration=8,max_duration=60,diagnostics=None):
    clean=sorted((s for s in segments if s.get('text','').strip() and 0<=s['start']<s['end']<=duration+.05),key=lambda s:s['start'])
    # Count actual candidate ranges, not hypothetical clips. Several windows can
    # describe the same moment, so rejection counts must never be presented as
    # an additional number of clips that the user could export.
    stats={'segments_considered':len(clean),'candidate_ranges':0,'below_score':0,
           'passed_score':0,'overlap_existing':0,'overlap_selected':0,
           'duplicate_existing':0,'duplicate_selected':0,'selected':0,
           'search_exhausted':True}
    candidates=[]
    for i,first in enumerate(clean):
        selected=[]
        for j in range(i,len(clean)):
            item=clean[j]
            if item['end']-first['start']>max_duration or (selected and item['start']-selected[-1]['end']>3):break
            selected.append(item)
            length=item['end']-first['start']
            if length>=(min_duration if duration>=min_duration else duration*.7) and (item['text'].rstrip().endswith((*ENDINGS,'?','؟')) or j==len(clean)-1):
                candidate=assess(selected,first['start'],min(item['end'],duration),measurements)
                stats['candidate_ranges']+=1
                if candidate['score']>=minimum_score:candidates.append(candidate)
                else:stats['below_score']+=1
    chosen=[]
    stats['passed_score']=len(candidates)
    excluded_signatures=[c.get('content_signature') or signature(' '.join(s['text'] for s in clean if s['start']<c['end'] and s['end']>c['start'])) for c in exclude]
    chosen_signatures=[]
    for index,candidate in enumerate(sorted(candidates,key=lambda c:(-c['score'],abs(c['end']-c['start']-30),c['start']))):
        if any(candidate['start']<c['end'] and candidate['end']>c['start'] for c in exclude):
            stats['overlap_existing']+=1;continue
        if any(candidate['start']<c['end'] and candidate['end']>c['start'] for c in chosen):
            stats['overlap_selected']+=1;continue
        if any(repeated(candidate['content_signature'],sig) for sig in excluded_signatures):
            stats['duplicate_existing']+=1;continue
        if any(repeated(candidate['content_signature'],sig) for sig in chosen_signatures):
            stats['duplicate_selected']+=1;continue
        chosen.append(candidate)
        chosen_signatures.append(candidate['content_signature'])
        if len(chosen)>=limit:
            stats['search_exhausted']=index+1==len(candidates)
            break
    stats['selected']=len(chosen)
    if diagnostics is not None:
        diagnostics.clear()
        diagnostics.update(stats)
    return chosen


def invalidate(clip):
    if clip.pop('selection_evidence',None) is not None:
        clip.update(score=None,reason='Selection changed. Review this edited range; previous engagement evidence was cleared.')
    clip.pop('content_signature',None)
