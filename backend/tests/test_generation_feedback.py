import pytest
from fastapi.testclient import TestClient
from backend import main,store,guest,selection


@pytest.mark.parametrize('text',[
    'आपकी वीडियो शुरुआत में लोग क्यों छोड़ देते हैं? क्योंकि आप नतीजा छिपाते हैं इसलिए पहले समाधान दिखाएं और फिर पूरी कहानी समझाएं।',
    'آپ کی ویڈیو شروع میں لوگ کیوں چھوڑ دیتے ہیں؟ کیونکہ آپ نتیجہ چھپاتے ہیں اس لیے پہلے حل دکھائیں اور پھر پوری کہانی سمجھائیں۔',
    'Aap ki video shuru mein log kyun chhor dete hain? Is liye pehle nateeja dikhao aur phir wajah samjhao taake aap ki baat poori ho.',
])
def test_native_hindi_urdu_and_roman_can_qualify_with_grounded_markers(text):
    clips=selection.highlights([{'start':0,'end':12,'text':text}],12,limit=100)
    assert len(clips)==1 and clips[0]['score']>=70
    assert clips[0]['selection_evidence']['opening_excerpt']==text
    assert selection.highlights([{'start':0,'end':12,'text':text}],12,limit=100,exclude=clips)==[]


def test_hindi_words_keep_combining_vowel_signs():
    assert selection.words('क्यों कैसे क्योंकि इसलिए।')==['क्यों','कैसे','क्योंकि','इसलिए']


def test_zero_results_explain_threshold_and_already_selected_ranges(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DATA',tmp_path)
    text='Why does your video lose viewers? Because you hide the result, show your audience the solution first and explain the lesson clearly.'
    with TestClient(main.app) as c:
        c.get('/api/session')
        store.save({'id':'feedback','owner_id':guest.owner_for_token(c.cookies.get(guest.COOKIE)),
                    'status':'ready','duration':12,'transcript':[{'id':0,'start':0,'end':12,'text':text}],'clips':[]})
        url='/api/projects/feedback/highlights'
        p=c.post(url,json={'clip_count':100,'minimum_score':100}).json()
        assert p['clip_generation']['created']==0
        assert p['clip_generation']['empty_reason']=='no_qualified_moments'
        assert 'Explore all' in p['clip_generation']['message']
        p=c.post(url,json={'clip_count':100,'minimum_score':70}).json()
        assert p['clip_generation']['created']==1 and p['clip_generation']['empty_reason'] is None
        original=p['clips']
        p=c.post(url,json={'clip_count':100,'minimum_score':70}).json()
        assert p['clip_generation']['created']==0 and p['clip_generation']['empty_reason']=='already_selected'
        assert p['clips']==original and 'already covered' in p['clip_generation']['message']
        p=c.post(url,json={'clip_count':100,'selection_mode':'all'}).json()
        assert p['clip_generation']['created']==0 and p['clip_generation']['empty_reason']=='already_selected'


def test_import_progress_uses_actual_private_project_state(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DATA',tmp_path)
    with TestClient(main.app) as c:
        c.get('/api/session')
        owner=guest.owner_for_token(c.cookies.get(guest.COOKIE))
        store.save({'id':'progress-project','owner_id':owner,'status':'transcribing','transcription_progress':37,
                    'clips':[{'status':'draft'}]})
        store.import_save({'id':'progress-job','owner_id':owner,'project_id':'progress-project','status':'processing'})
        progress=c.get('/api/imports/progress-job').json()['project_progress']
        assert progress=={'stage':'transcribing','transcription_progress':37,'total':1,'ready':0}
        store.mutate('progress-project',lambda p:p.update(status='ready',clips=[{'status':'ready'},{'status':'rendering'}]))
        assert c.get('/api/imports/progress-job').json()['project_progress']=={'stage':'rendering','transcription_progress':37,'total':2,'ready':1}
        c.cookies.clear();c.get('/api/session')
        assert c.get('/api/imports/progress-job').status_code==404


def four_distinct_moments():
    stories=[
        'Why do desert dunes sing when your feet disturb the sand? Because dry grains slide together, the result is a deep sound. Finally the experiment solved this unusual puzzle for researchers studying wind and landscapes.',
        'How can your camera capture distant galaxies through city lights? The solution uses carefully stacked exposures because faint stars need extra detail. Finally remove bright street lamps from view and compare the clear astronomical result.',
        'Why does your bread collapse inside a cold kitchen? Because yeast develops slowly without warmth, the mistake ruins its delicate structure. Finally measure flour with scales and give the dough enough time before baking tomorrow.',
        'How can you keep a bicycle moving uphill without exhaustion? The secret is choosing an easier gear because steep roads demand steady movement. Finally change your riding rhythm and learn this useful lesson during practice.',
    ]
    segments=[{'id':i,'start':i*120,'end':i*120+36,'text':text} for i,text in enumerate(stories)]
    segments.append({'id':4,'start':600,'end':636,'text':'And we discussed the ordinary schedule and the sequence of items for the following week. The meeting continued with the same agenda and nothing else was decided by the committee during the afternoon session.'})
    # Repeating the first story later must not increase the exportable count.
    segments.append({'id':5,'start':900,'end':936,'text':stories[0]})
    return segments


def test_requested_thirty_returns_four_with_actual_rejection_counts_and_no_padding(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DATA',tmp_path)
    with TestClient(main.app) as c:
        c.get('/api/session')
        store.save({'id':'thirty-requested','owner_id':guest.owner_for_token(c.cookies.get(guest.COOKIE)),
                    'status':'ready','duration':2400,'transcript':four_distinct_moments(),'clips':[]})
        options={'clip_count':30,'minimum_score':70,'min_duration':30,'max_duration':60}
        response=c.post('/api/projects/thirty-requested/highlights',json=options)
        assert response.status_code==200,response.text
        project=response.json();result=project['clip_generation'];stats=result['diagnostics']
        assert result['requested']==30 and result['created']==len(project['clips'])==4
        assert 'Only 4 new clips' in result['message']
        assert 'current settings' in result['shortfall_message'] and 'maximum' in result['shortfall_message']
        assert result['duration_capacity']==80  # The source length is not this shortage's cause.
        assert stats['candidate_ranges']==6 and stats['below_score']==1 and stats['passed_score']==5
        assert stats['duplicate_selected']==1 and stats['selected']==4 and stats['search_exhausted'] is True
        assert '1 near-duplicate ranges' in result['message']
        assert all(30<=clip['end']-clip['start']<=60 and clip['score']>=70 for clip in project['clips'])
        original=project['clips']
        repeated=c.post('/api/projects/thirty-requested/highlights',json=options).json()
        result=repeated['clip_generation'];stats=result['diagnostics']
        assert repeated['clips']==original and result['created']==0
        assert result['empty_reason']=='already_selected'
        assert stats['overlap_existing']==4 and stats['duplicate_existing']==1
        assert 'already covered' in result['message']


def test_diagnostics_does_not_claim_exhaustion_when_requested_limit_stops_search():
    stats={}
    clips=selection.highlights(four_distinct_moments(),2400,limit=1,min_duration=30,max_duration=60,diagnostics=stats)
    assert len(clips)==stats['selected']==1
    assert stats['search_exhausted'] is False
    assert stats['candidate_ranges']==stats['below_score']+stats['passed_score']


def test_no_duration_matched_ranges_are_distinct_from_score_rejections():
    stats={}
    clips=selection.highlights([{'start':0,'end':12,'text':four_distinct_moments()[0]['text']}],2400,
                               limit=30,min_duration=30,max_duration=60,diagnostics=stats)
    assert clips==[] and stats['candidate_ranges']==stats['below_score']==stats['passed_score']==0
    assert stats['segments_considered']==1 and stats['search_exhausted'] is True
