import pytest
from fastapi.testclient import TestClient
from backend import guest,main,media,store


def speech():
    topics=['camera settings','podcast sound','gaming mistakes','cooking recipes','fitness routine','travel budget','business prices','music practice','coding errors','garden tools','study methods','painting colors']
    return [{'id':i,'start':i*8,'end':(i+1)*8,'text':f'Why improve {topic}? Because the solution saves your audience time and gives you one useful lesson.'} for i,topic in enumerate(topics)]


@pytest.mark.parametrize('mode',['quality','all'])
@pytest.mark.parametrize('bounds',[(8,12),(16,24),(60,90)])
def test_requested_count_and_duration_survive_generation(tmp_path,monkeypatch,mode,bounds):
    monkeypatch.setattr(store,'DATA',tmp_path)
    with TestClient(main.app) as client:
        client.get('/api/session')
        store.save({'id':'duration-test','owner_id':guest.owner_for_token(client.cookies.get(guest.COOKIE)),
                    'status':'ready','duration':96,'transcript':speech(),'clips':[]})
        a,b=bounds
        r=client.post('/api/projects/duration-test/highlights',json={'selection_mode':mode,'minimum_score':0,'clip_count':2,'min_duration':a,'max_duration':b})
        assert r.status_code==200,r.text
        p=r.json()
        assert 0<len(p['clips'])<=2
        assert p['min_duration']==a and p['max_duration']==b
        assert p['clip_generation']['min_duration']==a and p['clip_generation']['max_duration']==b
        assert all(a<=c['end']-c['start']<=b for c in p['clips'])
        before=p['clips']
        r=client.post('/api/projects/duration-test/highlights',json={'clip_count':2,'min_duration':40,'max_duration':10})
        assert r.status_code==422
        assert client.get('/api/projects/duration-test').json()['clips']==before


def test_explore_never_exceeds_maximum_for_one_long_segment():
    assert media.highlights([{'start':0,'end':70,'text':'Why? Because this is a long continuous transcript segment.'}],70,min_duration=15,max_duration=30)==[]


def test_import_accepts_same_count_and_duration_validation():
    p=main.LinkImportInput(url='https://example.com/video.mp4',clip_count=17,min_duration=20,max_duration=45)
    assert (p.clip_count,p.min_duration,p.max_duration)==(17,20,45)
    with pytest.raises(ValueError):
        main.LinkImportInput(url='https://example.com/video.mp4',min_duration=60,max_duration=15)


@pytest.mark.parametrize('mode',['quality','all'])
def test_short_source_preserves_complete_speech_before_trailing_pause(mode):
    p={'duration':3,'selection_mode':mode,'minimum_score':0,'transcript':[{'start':0,'end':2.4,'text':'Why improve your videos? Because the solution is to show the result first.'}],'clips':[],'min_duration':8,'max_duration':60}
    main.add_highlights(p,5)
    assert len(p['clips'])==1 and p['clips'][0]['end']==2.4
    assert 'Short source' in p['clip_generation']['message']
