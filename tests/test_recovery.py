"""Recovery keeps downloaded speech, ownership and explicit quality settings."""
from contextlib import contextmanager
from copy import deepcopy
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend import guest, main, selection, store


def source_speech():
    return [{'id':0,'start':1.25,'end':12.5,'text':'Descubri el secreto porque finalmente consegui el resultado.',
             'words':[{'word':'Descubri','start':1.25,'end':2.1},
                      {'word':' el secreto','start':2.1,'end':5.5},
                      {'word':' porque finalmente consegui el resultado.','start':5.5,'end':12.5}]}]


@pytest.fixture
def workspace(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DATA',tmp_path)
    # Unsupported-route tests must not depend on optional installed Spanish models.
    monkeypatch.setattr(main.translation,'ROOT',tmp_path/'translation-models')
    with TestClient(main.app) as client:
        client.get('/api/session')
        project={'id':'recovery-source','owner_id':guest.owner_for_token(client.cookies.get(guest.COOKIE)),
                 'status':'error','error':'Unsupported local translation','duration':2490.041,'has_audio':True,
                 'language':'es','caption_script':'roman_urdu','requested_clip_count':43,
                 'min_duration':60,'max_duration':90,'minimum_score':84,'selection_mode':'quality',
                 'transcript':[],'source_transcript':source_speech(),
                 'clips':[{'id':'existing','title':'Kept clip','start':30,'end':95,'score':91,
                           'status':'ready','file':'existing-revision.mp4'}]}
        store.save(project)
        folder=tmp_path/project['id'];folder.mkdir()
        (folder/'source').write_bytes(b'Preserved downloaded source fixture')
        calls=[]
        monkeypatch.setattr(main.pool,'submit',lambda fn,*args:calls.append((fn,args)))
        yield client,project,calls


def test_unsupported_translation_keeps_original_words_and_requested_choice(workspace,monkeypatch):
    _,project,_=workspace
    def unexpected_conversion(*args):
        pytest.fail('Unsupported translation must not call a translator or invent speech.')
    monkeypatch.setattr(main.translation,'convert_segments',unexpected_conversion)
    original=source_speech()
    result=main.convert_project_captions(project['id'],original,'es','roman_urdu')
    assert result==original and result is not original
    assert result[0]['words'] is not original[0]['words']
    saved=store.get(project['id'])
    assert saved['caption_script']=='original' and saved['requested_caption_script']=='roman_urdu'
    assert 'Spanish' in saved['caption_warning'] and 'original-language' in saved['caption_warning']
    result[0]['words'][0]['word']='Changed independently'
    assert store.get(project['id'])['source_transcript']==source_speech()


def test_original_subtitles_clear_stale_warning_without_translation(workspace):
    _,project,_=workspace
    store.mutate(project['id'],lambda p:p.update(caption_warning='Previous conversion warning'))
    assert main.convert_project_captions(project['id'],source_speech(),'es','original')==source_speech()
    assert store.get(project['id'])['caption_warning'] is None


def test_missing_core_translation_model_keeps_original_captions_with_actionable_notice(workspace,monkeypatch):
    _,project,_=workspace
    def missing(*args):raise ValueError('Translation model is missing.')
    monkeypatch.setattr(main.translation,'convert_segments',missing)
    result=main.convert_project_captions(project['id'],source_speech(),'en','urdu')
    assert result==source_speech()
    saved=store.get(project['id'])
    assert saved['caption_script']=='original' and saved['requested_caption_script']=='urdu'
    assert saved['source_transcript']==source_speech()
    assert 'no installed model route' in saved['caption_warning']


def test_process_saves_detected_language_and_words_before_translation_failure(workspace,monkeypatch):
    _,project,_=workspace
    @contextmanager
    def audio(source):yield source
    word=SimpleNamespace(word='Descubri',start=1.25,end=2.1)
    segment=SimpleNamespace(start=1.25,end=12.5,text='Descubri el secreto.',words=[word])
    monkeypatch.setattr(main.speech,'timeline_audio',audio)
    monkeypatch.setattr(main.speech,'load_model',lambda *args:object())
    monkeypatch.setattr(main.speech,'transcribe',lambda *args,**kwargs:(iter([segment]),SimpleNamespace(language='es')))
    monkeypatch.setattr(main,'model',None)
    monkeypatch.setattr(main,'models',{})
    def fail(*args):raise ValueError('Translator failed after speech recognition')
    monkeypatch.setattr(main,'convert_project_captions',fail)
    store.mutate(project['id'],lambda p:p.update(language=None,source_transcript=[]))
    main.process(project['id'])
    saved=store.get(project['id'])
    assert saved['status']=='error' and saved['language']=='es'
    assert saved['source_transcript'][0]['words']==[{'word':'Descubri','start':1.25,'end':2.1}]
    assert saved['transcript']==[] and 'Translator failed' in saved['error']


def test_process_unsupported_requested_translation_finishes_with_original_speech(workspace,monkeypatch):
    _,project,_=workspace
    @contextmanager
    def audio(source):yield source
    original=source_speech()[0]
    segment=SimpleNamespace(start=original['start'],end=original['end'],text=original['text'],
                            words=[SimpleNamespace(**word) for word in original['words']])
    monkeypatch.setattr(main.speech,'timeline_audio',audio)
    monkeypatch.setattr(main.speech,'load_model',lambda *args:object())
    monkeypatch.setattr(main.speech,'transcribe',lambda *args,**kwargs:(iter([segment]),SimpleNamespace(language='es')))
    monkeypatch.setattr(main,'prepare_analysis',lambda project_id:None)
    monkeypatch.setattr(main,'model',None)
    monkeypatch.setattr(main,'models',{})
    def no_translation(*args):pytest.fail('Spanish was not translated by the local Urdu/Hindi/English translator.')
    monkeypatch.setattr(main.translation,'convert_segments',no_translation)
    main.process(project['id'])
    saved=store.get(project['id'])
    assert saved['status']=='ready' and saved['error'] is None and saved['language']=='es'
    assert saved['transcript']==saved['source_transcript']==source_speech()
    assert saved['caption_script']=='original' and saved['requested_caption_script']=='roman_urdu'
    assert 'Spanish' in saved['caption_warning'] and saved['clip_generation']['created']==0
    assert saved['clips']==project['clips'] and saved['minimum_score']==84


def test_recovery_reuses_speech_preserves_strict_rules_and_existing_clips(workspace,monkeypatch):
    client,project,calls=workspace
    store.import_save({'id':'failed-import','owner_id':project['owner_id'],'project_id':project['id'],
                       'status':'error','error':'Unsupported translation'})
    def no_repeat(*args,**kwargs):pytest.fail('Recovery must not repeat download or recognition.')
    monkeypatch.setattr(main.importer,'download_video',no_repeat)
    monkeypatch.setattr(main.speech,'transcribe',no_repeat)
    monkeypatch.setattr(main.speech,'load_model',no_repeat)
    monkeypatch.setattr(main.translation,'convert_segments',no_repeat)
    response=client.post(f"/api/projects/{project['id']}/recover")
    assert response.status_code==202,response.text
    assert response.json()['status']=='analyzing' and response.json()['error'] is None
    assert calls==[(main.recover_saved_speech,(project['id'],))]
    fn,args=calls.pop();fn(*args)
    saved=store.get(project['id'])
    assert saved['status']=='ready' and saved['error'] is None and saved['processing_message'] is None
    assert saved['transcript']==project['source_transcript']
    assert saved['source_transcript']==project['source_transcript']
    assert saved['clips']==project['clips']
    assert saved['language']=='es' and saved['caption_script']=='original'
    assert saved['requested_caption_script']=='roman_urdu'
    assert (saved['requested_clip_count'],saved['minimum_score'],saved['selection_mode'])==(43,84,'quality')
    assert (saved['min_duration'],saved['max_duration'])==(60,90)
    assert saved['clip_generation']['created']==0
    assert saved['clip_generation']['empty_reason']=='no_qualified_moments'
    assert store.import_get('failed-import')['status']=='ready'
    assert store.import_get('failed-import')['error'] is None


def test_recovery_queues_only_new_previews(workspace,monkeypatch):
    client,project,calls=workspace
    store.mutate(project['id'],lambda p:p.update(min_duration=8,max_duration=20))
    def generated(p,count):
        assert count==43
        p['clips'].append({'id':'fresh','batch_id':'new-batch','status':'draft','file':None})
        p['clip_generation']={'batch_id':'new-batch','created':1}
    monkeypatch.setattr(main,'add_highlights',generated)
    renders=[]
    monkeypatch.setattr(main.render_pool,'submit',lambda fn,*args:renders.append((fn,args)))
    assert client.post(f"/api/projects/{project['id']}/recover").status_code==202
    fn,args=calls.pop();fn(*args)
    assert renders==[(main.render_clip,(project['id'],'fresh'))]
    assert store.get(project['id'])['clips'][0]==project['clips'][0]
    assert store.get(project['id'])['clips'][1]['status']=='queued'


def test_recovery_settings_change_only_when_explicitly_selected(workspace):
    client,project,calls=workspace
    response=client.post(f"/api/projects/{project['id']}/recover",json={'selection_mode':'all','minimum_score':60})
    assert response.status_code==202
    saved=store.get(project['id'])
    assert (saved['selection_mode'],saved['minimum_score'])==('all',60)
    assert (saved['min_duration'],saved['max_duration'],saved['requested_clip_count'])==(60,90,43)
    assert len(calls)==1


@pytest.mark.parametrize('options',[{'minimum_score':101},{'minimum_score':True},{'selection_mode':'automatic'}])
def test_invalid_recovery_settings_do_not_mutate_project(workspace,options):
    client,project,calls=workspace
    assert client.post(f"/api/projects/{project['id']}/recover",json=options).status_code==422
    assert store.get(project['id'])==project and not calls


def test_recovery_remains_private_and_does_not_leak_saved_speech(workspace):
    client,project,calls=workspace
    with TestClient(main.app) as outsider:
        assert outsider.post(f"/api/projects/{project['id']}/recover").status_code==401
        outsider.get('/api/session')
        response=outsider.post(f"/api/projects/{project['id']}/recover",json={'minimum_score':0,'selection_mode':'all'})
        assert response.status_code==404 and 'Descubri' not in response.text
        assert client.post('/api/projects/missing/recover').status_code==404
    assert store.get(project['id'])==project and not calls


@pytest.mark.parametrize('busy',['queued','transcribing','analyzing','clip_queued','clip_rendering','import_processing'])
def test_recovery_cannot_race_active_processing(workspace,busy):
    client,project,calls=workspace
    if busy.startswith('clip_'):
        store.mutate(project['id'],lambda p:p['clips'][0].update(status=busy[5:]))
    elif busy=='import_processing':
        store.import_save({'id':'busy-import','owner_id':project['owner_id'],'project_id':project['id'],'status':'processing'})
    else:store.mutate(project['id'],lambda p:p.update(status=busy))
    before=store.get(project['id'])
    assert client.post(f"/api/projects/{project['id']}/recover").status_code==409
    assert store.get(project['id'])==before and not calls


@pytest.mark.parametrize('missing',['speech','video','empty_video'])
def test_recovery_requires_saved_speech_and_existing_source(workspace,missing):
    client,project,calls=workspace
    if missing=='speech':store.mutate(project['id'],lambda p:p.update(source_transcript=[]))
    elif missing=='video':(store.DATA/project['id']/'source').unlink()
    else:(store.DATA/project['id']/'source').write_bytes(b'')
    before=store.get(project['id'])
    response=client.post(f"/api/projects/{project['id']}/recover")
    assert response.status_code==400 and ('source transcript' if missing=='speech' else 'source video') in response.json()['detail']
    assert store.get(project['id'])==before and not calls


def test_recovery_missing_direct_project_is_not_queued(workspace):
    _,_,calls=workspace
    with pytest.raises(HTTPException) as missing:main.recover_project('missing')
    assert missing.value.status_code==404 and not calls


def test_recovery_cannot_escape_the_project_source_directory(workspace):
    with pytest.raises(HTTPException) as invalid:main.recovery_source('..')
    assert invalid.value.status_code==400 and 'path' in invalid.value.detail


def test_recovery_duplicate_request_cannot_queue_a_second_job(workspace):
    client,project,calls=workspace
    path=f"/api/projects/{project['id']}/recover"
    assert client.post(path).status_code==202
    assert client.post(path).status_code==409
    assert calls==[(main.recover_saved_speech,(project['id'],))]


def test_recovery_failure_clears_progress_and_keeps_source(workspace,monkeypatch):
    client,project,calls=workspace
    store.import_save({'id':'failed-import','owner_id':project['owner_id'],'project_id':project['id'],'status':'error'})
    assert client.post(f"/api/projects/{project['id']}/recover").status_code==202
    def fail(*args):raise ValueError('Could not prepare saved highlights')
    monkeypatch.setattr(main,'add_highlights',fail)
    fn,args=calls.pop();fn(*args)
    saved=store.get(project['id'])
    assert saved['status']=='error' and saved['processing_message'] is None
    assert 'Could not prepare saved highlights' in saved['error']
    assert saved['source_transcript']==project['source_transcript'] and saved['clips']==project['clips']
    assert store.import_get('failed-import')['status']=='error'


def test_duration_capacity_explains_why_45_one_minute_clips_cannot_fit():
    project={'duration':2490.041,'source_transcript':source_speech(),'transcript':[],
             'clips':[],'selection_mode':'quality','minimum_score':84,'min_duration':60,'max_duration':90}
    main.add_highlights(project,45)
    result=project['clip_generation']
    assert result['requested']==45 and result['created']==0 and result['duration_capacity']==41
    assert 'at most 41 non-overlapping clips' in result['message'] and 'shorter duration' in result['message']
    assert project['minimum_score']==84 and project['selection_mode']=='quality' and project['clips']==[]


def test_spanish_selection_grounds_explanation_in_actual_hook_and_payoff_words():
    text='Cómo evitar este error en tus videos? Porque mostrar el resultado primero es la solución que finalmente aprendí.'
    speech=[{'id':0,'start':0,'end':12,'text':text}]
    clips=selection.highlights(speech,12,minimum_score=70)
    assert len(clips)==1 and clips[0]['score']>=70
    assert clips[0]['selection_evidence']['opening_excerpt']==text
    assert 'error' in clips[0]['reason'] and 'porque' in clips[0]['reason']
    assert selection.highlights(speech,12,minimum_score=100)==[]
    weak=[{'id':0,'start':0,'end':12,'text':'La reunión empieza por la mañana y todos leen la lista de tareas para la semana.'}]
    assert selection.highlights(weak,12,minimum_score=70)==[]


def test_registered_processing_failure_does_not_claim_source_is_private(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DATA',tmp_path)
    job_id='registered-import'
    store.import_save({'id':job_id,'owner_id':'owner','status':'queued',
                       'options':{'url':'https://example.com/public.mp4','caption_script':'roman_urdu'}})
    def downloaded(url,folder,progress,**kwargs):
        folder.mkdir();path=folder/'downloaded.mp4';path.write_bytes(b'Existing video bytes')
        return {'path':path,'name':'Public video','platform':'fixture'}
    monkeypatch.setattr(main.importer,'download_video',downloaded)
    monkeypatch.setattr(main.media,'probe',lambda *args:{'duration':90,'has_audio':True})
    monkeypatch.setattr(main.media,'run',lambda *args,**kwargs:None)
    def processing_failed(project_id):
        store.mutate(project_id,lambda p:p.update(status='error',error='Translation model is missing.',source_transcript=source_speech()))
    monkeypatch.setattr(main,'process',processing_failed)
    def wrong_advice(*args):pytest.fail('Downloaded video processing errors are not downloader/private-link errors.')
    monkeypatch.setattr(main.importer,'clean_error',wrong_advice)
    main.run_link_import(job_id)
    result=store.import_get(job_id)
    assert result['status']=='error' and result['project_id']==job_id
    assert 'Translation model is missing' in result['error'] and 'saved source transcript are kept' in result['error']
    assert 'Public video links only' not in result['error'] and 'private/login-only' not in result['error']
    assert (tmp_path/job_id/'source').read_bytes()==b'Existing video bytes'
    assert store.get(job_id)['source_transcript']==source_speech()
