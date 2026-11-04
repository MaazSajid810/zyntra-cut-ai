import pytest
from fastapi.testclient import TestClient
from backend import analysis,main,store,guest,media,selection

TEXT='Why does your audience leave? Because you hide the result, show your audience the solution first and explain one useful lesson.'

@pytest.fixture
def measured_source(tmp_path):
    source=tmp_path/'measured.mp4'
    media.run(['-f','lavfi','-i','color=c=black:s=160x90:r=10:d=3',
               '-f','lavfi','-i','color=c=white:s=160x90:r=10:d=3',
               '-f','lavfi','-i',r'aevalsrc=if(between(t\,1\,5)\,0.4*sin(2*PI*440*t)\,0):s=8000:d=6',
               '-filter_complex','[0:v][1:v]concat=n=2:v=1:a=0[v]',
               '-map','[v]','-map','2:a','-c:v','libx264','-c:a','aac','-t','6',str(source)])
    return source


def test_real_scene_silence_energy_and_waveform_measurements(measured_source):
    result=analysis.inspect_source(measured_source,6)
    assert result['version']==analysis.VERSION
    assert len(result['waveform'])>=11
    assert any(abs(t-3)<.6 for t in result['scene_changes'])
    assert any(a==0 and .5<=b<=1.5 for a,b in result['silences'])
    assert any(a>=4.5 and b==6 for a,b in result['silences'])
    assert max(result['waveform'])>.1
    quiet=analysis.interval_evidence(result,0,.5)
    voice=analysis.interval_evidence(result,2,3)
    assert quiet['silence_fraction']>voice['silence_fraction']
    assert quiet['audio_energy']<voice['audio_energy']
    assert voice['scene_changes']==0
    silent=analysis.inspect_source(measured_source,6,has_audio=False)
    assert not silent['waveform'] and not silent['audio_db']
    assert silent['visual_change']


def test_auto_quantity_cached_analysis_source_ranking_and_guest_isolation(measured_source,tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DATA',tmp_path/'projects');store.DATA.mkdir()
    with TestClient(main.app) as c:
        c.get('/api/session')
        with measured_source.open('rb') as f:r=c.post('/api/projects',files={'file':('measured.mp4',f,'video/mp4')})
        assert r.status_code==201,r.text
        pid=r.json()['id'];base=f'/api/projects/{pid}'
        def transcript(p):
            p.update(status='ready',transcript=[{'id':0,'start':0,'end':6,'text':'Translated display text.'}],source_transcript=[{'id':0,'start':0,'end':6,'text':TEXT}])
        store.mutate(pid,transcript)
        result=c.post(base+'/highlights',json={'auto_count':True,'minimum_score':60,'min_duration':8,'max_duration':60})
        assert result.status_code==200,result.text
        p=result.json();assert p['auto_count'] and p['clip_generation']['auto_count']
        assert p['clip_generation']['created']==1
        assert 'Short source' in p['clip_generation']['message']
        clip=p['clips'][0];assert clip['end']<=p['duration']
        assert clip['selection_evidence']['opening_excerpt']==TEXT
        assert 'measured-media' in clip['selection_evidence']['method']
        assert 'audio_energy' in clip['selection_evidence']['factors']
        def fail(*a,**k):raise AssertionError('Cached measurements must be reused')
        monkeypatch.setattr(analysis,'inspect_source',fail)
        assert c.post(base+'/highlights',json={'auto_count':True,'minimum_score':60}).json()['clip_generation']['created']==0
        with TestClient(main.app) as other:
            other.get('/api/session');assert other.get(base).status_code==404
        assert (store.DATA/pid/'source').exists()

@pytest.mark.parametrize('body',[{'min_duration':61,'max_duration':30},{'min_duration':0},{'max_duration':181},{'clip_count':0}])
def test_duration_validation(body):
    with pytest.raises(ValueError):main.GenerationInput.model_validate(body)


def test_measured_loudness_cannot_promote_a_weak_hook():
    weak=[{'start':0,'end':12,'text':'And we had the normal meeting about the ordinary items on the calendar.'}]
    measured={'sample_seconds':.5,'audio_db':[-1]*24,'visual_change':[1]*24,'silences':[],'scene_changes':[],'limitations':'Measured, not predictions.'}
    assert not selection.highlights(weak,12,measurements=measured)
    assert selection.highlights([{'start':0,'end':5,'text':TEXT}],5,minimum_score=60)


def test_analysis_claim_and_honest_failure_fallback(measured_source,tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DATA',tmp_path/'protected');store.DATA.mkdir()
    with TestClient(main.app) as c:
        c.get('/api/session')
        with measured_source.open('rb') as f:
            p=c.post('/api/projects',files={'file':('protected.mp4',f,'video/mp4')}).json()
        pid=p['id'];base=f'/api/projects/{pid}'
        c.put(base+'/transcript',json=[{'id':0,'start':0,'end':6,'text':TEXT}])
        def unavailable(*args,**kwargs):
            assert store.get(pid)['status']=='analyzing'
            concurrent=TestClient(main.app)
            concurrent.cookies.update(c.cookies)
            try:
                assert concurrent.delete(base).status_code==409
                assert concurrent.put(base+'/transcript',json=[]).status_code==409
                assert concurrent.post(base+'/highlights',json={}).status_code==409
            finally:concurrent.close()
            raise RuntimeError('test analysis unavailable')
        monkeypatch.setattr(analysis,'inspect_source',unavailable)
        result=c.post(base+'/highlights',json={'minimum_score':60})
        assert result.status_code==200,result.text
        p=result.json();assert p['status']=='ready'
        assert 'transcript ranking only' in p['analysis_error']
        assert 'media_analysis' not in p
        assert p['clips'][0]['selection_evidence']['method']=='transcript-heuristic-v2'
        assert (store.DATA/pid/'source').exists()


def test_short_audio_keeps_video_timeline(measured_source,tmp_path):
    short=tmp_path/'short.m4a';source=tmp_path/'short-audio.mp4'
    media.run(['-i',str(measured_source),'-t','2','-vn','-c:a','aac',str(short)])
    media.run(['-i',str(measured_source),'-i',str(short),'-map','0:v:0','-map','1:a:0','-c','copy',str(source)])
    measured=analysis.inspect_source(source,6)
    assert len(measured['audio_db'])==12
    assert measured['waveform'][-1]==0
    assert any(a<=3 and b==6 for a,b in measured['silences'])


def test_sparse_keyframes_use_actual_timestamps_and_keep_full_audio(measured_source,monkeypatch):
    monkeypatch.setattr(analysis,'LONG_SOURCE_SECONDS',0)
    measured=analysis.inspect_source(measured_source,6)
    assert measured['visual_sample_mode']=='keyframes'
    assert measured['visual_scan_complete']
    assert len(measured['visual_sample_times'])==len(measured['visual_change'])
    assert measured['visual_sample_times']==sorted(measured['visual_sample_times'])
    assert len(measured['audio_db'])==12
    assert any(abs(moment-3)<.6 for moment in measured['scene_changes'])
    assert 'keyframes' in measured['limitations']
    # A window without a sampled frame must not inherit another time's activity.
    gap={'sample_seconds':.5,'visual_sample_times':[0,5],'visual_change':[0,1],
         'audio_db':[-20]*12,'silences':[],'scene_changes':[5]}
    assert analysis.interval_evidence(gap,1,2)['visual_activity'] is None
    assert analysis.interval_evidence(gap,5,6)['visual_activity']==100


def test_sparse_visual_budget_does_not_invent_unscanned_results(measured_source,monkeypatch):
    monkeypatch.setattr(analysis,'LONG_SOURCE_SECONDS',0)
    monkeypatch.setattr(analysis,'VISUAL_BUDGET_SECONDS',0)
    measured=analysis.inspect_source(measured_source,6)
    assert measured['visual_scan_complete'] is False
    assert measured['visual_sample_times']==[]
    assert measured['visual_change']==[]
    assert len(measured['audio_db'])==12
    assert analysis.interval_evidence(measured,0,6)['visual_activity'] is None
    assert 'time budget' in measured['limitations']
