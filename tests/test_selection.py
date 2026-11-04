import pytest
from fastapi.testclient import TestClient
from backend import selection,main,store,guest,media


def strong(start=0):
    return [
        {'start':start,'end':start+8,'text':'Why does your video lose every viewer in the first three seconds? Here is the mistake you can fix.'},
        {'start':start+8,'end':start+16,'text':'The solution is to show the result first because your audience needs a reason to keep watching.'},
        {'start':start+16,'end':start+24,'text':'Finally remove the long introduction and give your audience one clear lesson they can use today.'},
    ]


def test_quality_rejects_empty_and_weak_content_instead_of_filling_count():
    assert selection.highlights([],100,100)==[]
    weak=[{'start':0,'end':20,'text':'And we continued the ordinary discussion of the schedule and the list of items for the following week.'}]
    assert selection.highlights(weak,100,100)==[]


def test_quality_selects_grounded_complete_moment_and_deduplicates_repeated_story():
    transcript=strong()+strong(80)
    selected=selection.highlights(transcript,110,limit=100)
    assert len(selected)==1
    c=selected[0]
    assert c['score']>=70 and c['start']==0
    assert c['end'] in [8,16,24]
    assert 'transcript-heuristic' in c['selection_evidence']['method']
    assert c['selection_evidence']['opening_excerpt']==transcript[0]['text']
    assert selection.highlights(transcript,110,100,exclude=selected)==[]


def test_quality_threshold_and_existing_manual_clip_are_respected():
    assert selection.highlights(strong(),24,minimum_score=100)==[]
    assert selection.highlights(strong(),24,exclude=[{'start':0,'end':24}])==[]
    selected=selection.highlights(strong(),24)
    assert selected
    assert all(0<=c['start']<c['end']<=24 for c in selected)


def test_quality_scores_opening_not_keywords_buried_later():
    weak_opening=[{'start':0,'end':8,'text':'And it was the same ordinary sequence of events in the meeting.'},*strong(8)[1:]]
    # No segment with a strong opening survives by borrowing hook words from later.
    assert selection.highlights(weak_opening,40)==[]


def test_quality_api_defaults_and_threshold_validation(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DATA',tmp_path)
    with TestClient(main.app) as client:
        client.get('/api/session')
        store.save({'id':'quality-test','owner_id':guest.owner_for_token(client.cookies.get(guest.COOKIE)),
            'status':'ready','duration':120,'transcript':strong()+strong(80),'clips':[]})
        for value in [-1,101,70.5,True]:
            assert client.post('/api/projects/quality-test/highlights',json={'minimum_score':value}).status_code==422
        result=client.post('/api/projects/quality-test/highlights',json={'clip_count':100})
        assert result.status_code==200,result.text
        p=result.json()
        assert p['selection_mode']=='quality'
        assert 0<len(p['clips'])<100
        assert 'maximum' in p['clip_generation']['message']
        assert all(c['status']=='draft' and c['file'] is None for c in p['clips'])
        before=p['clips']
        p=client.post('/api/projects/quality-test/highlights',json={'clip_count':100}).json()
        assert p['clips']==before and p['clip_generation']['created']==0
        c=before[0]
        body={'title':c['title'],'start':c['start'],'end':c['end']-1}
        edited=client.put(f"/api/projects/quality-test/clips/{c['id']}",json=body)
        assert edited.status_code==200,edited.text
        assert edited.json()['clips'][0]['score'] is None
        assert 'selection_evidence' not in edited.json()['clips'][0]


def test_caption_phrases_preserve_words_and_segment_bounds():
    segment={'start':10,'end':24,'text':'These are actual source words that should appear as short readable phrases rather than one giant paragraph covering the video.'}
    cues=list(media.readable_cues(segment))
    assert len(cues)>1
    assert ' '.join(c['text'] for c in cues)==segment['text']
    assert cues[0]['start']==10 and cues[-1]['end']==24
    assert all(a['end']==pytest.approx(b['start']) for a,b in zip(cues,cues[1:]))
    assert all(len(c['text'].split())<=7 for c in cues)


def test_question_without_payoff_does_not_qualify():
    assert selection.highlights([{'start':0,'end':12,'text':'Why does this always happen? You will never believe the secret we are about to show you.'}],12)==[]


def test_edited_selection_cannot_keep_stale_score():
    c=selection.highlights(strong(),24)[0]
    selection.invalidate(c)
    assert c['score'] is None
    assert 'selection_evidence' not in c and 'content_signature' not in c
