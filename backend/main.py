import logging
import json
import mimetypes
import shutil
import os
import threading
import uuid
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Literal
from copy import deepcopy

from fastapi import Depends, FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, Field, model_validator

from . import guest, importer, media, speech, store, selection, romanization, assets, translation, analysis, workspace as platform, dubbing, thumbnails, compositor
from .languages import SpeechLanguage, CaptionScript, SPEECH_NAMES, CAPTION_TARGETS, caption_name, capability_catalog

log = logging.getLogger('clipforge')
pool = ThreadPoolExecutor(max_workers=1)
RENDER_WORKERS = max(1,min(2,int(os.environ.get('CLIPFORGE_RENDER_WORKERS','2'))))
render_pool = ThreadPoolExecutor(max_workers=RENDER_WORKERS)
import_pool = ThreadPoolExecutor(max_workers=1)
cleanup_pool = ThreadPoolExecutor(max_workers=1)
model = None
models = {}
model_lock = threading.Lock()

class GenerationInput(BaseModel):
    clip_count: int = Field(default=5, ge=1, le=100, strict=True)
    auto_count: bool = False
    min_duration: float = Field(default=8,ge=3,le=180)
    max_duration: float = Field(default=60,ge=3,le=180)
    transcription_mode: Literal['fast','quick','balanced','accurate'] = 'balanced'
    speech_language: SpeechLanguage = 'auto'
    caption_script: CaptionScript = 'original'
    selection_mode: Literal['quality','all'] = 'quality'
    minimum_score: int = Field(default=70,ge=0,le=100,strict=True)
    redo: bool = False
    auto_render: bool = False
    background: bool = False
    generated_settings: dict | None = None

    @model_validator(mode='after')
    def safe_generated_settings(self):
        if self.min_duration>self.max_duration:raise ValueError('Minimum clip duration must not exceed maximum duration.')
        if self.generated_settings is not None:
            self.generated_settings=EffectSettings.model_validate(self.generated_settings).model_dump()
        return self

def prepare_analysis(project_id):
    p=project_or_404(project_id)
    if p.get('media_analysis',{}).get('version')==analysis.VERSION:return
    source=store.DATA/project_id/'source'
    if not source.is_file():return  # Metadata-only fixtures/legacy records: no invented measurements.
    store.mutate(project_id,lambda p:p.update(processing_message='Measuring audio, silence and visual changes…'))
    try:
        measured=analysis.inspect_source(source,p['duration'],p.get('has_audio',True))
        store.mutate(project_id,lambda p:p.update(media_analysis=measured,analysis_error=None))
    except Exception as exc:
        log.warning('Media measurements unavailable',exc_info=True)
        store.mutate(project_id,lambda p:p.update(analysis_error=f'Media measurements unavailable; transcript ranking only: {exc}'))


def add_highlights(p, count):
    quality=p.get('selection_mode','quality')=='quality'
    auto=p.get('auto_count',False)
    count=100 if auto else count
    source=p.get('source_transcript') or p['transcript']
    diagnostics={}
    def ranked(exclude=(),limit=count):
        return selection.highlights(source,p['duration'],limit=limit,exclude=exclude,minimum_score=p.get('minimum_score',70),
            measurements=p.get('media_analysis'),min_duration=p.get('min_duration',8),max_duration=p.get('max_duration',60),diagnostics=diagnostics)
    def explored(exclude=(),limit=count):
        return media.highlights(source,p['duration'],limit=limit,exclude=exclude,min_duration=p.get('min_duration',8),max_duration=p.get('max_duration',60))
    suggestions = ranked(p['clips']) if quality else explored(p['clips'])
    batch_id = uuid.uuid4().hex
    for c in suggestions:
        c.update(**EffectSettings().model_dump(),id=uuid.uuid4().hex, batch_id=batch_id, status='draft', file=None, error=None)
        c.update(p.get('default_effects',{}))
        c.update(sticker='none',sticker_enabled=False)
    p['clips'].extend(suggestions)
    created = len(suggestions)
    empty_reason=None
    if not created:
        # Quality diagnostics already explain whether eligible ranges were
        # covered. Avoid repeating the full transcript scan for an empty batch.
        covered=bool(diagnostics.get('passed_score')) if quality else bool(explored(limit=1))
        empty_reason='already_selected' if covered and p['clips'] else 'no_qualified_moments' if quality else 'insufficient_material'
    shortfall=None
    if created<count:
        shortfall=(f'Only {created} new clips could be selected with the current settings; '
                   f'{count} is your requested maximum, not a guaranteed quantity.')
    p['clip_generation'] = {
        'requested': count, 'created': created, 'batch_id': batch_id, 'empty_reason':empty_reason,
        'shortfall_message':shortfall,
        'message': f'Created {created} of {count} requested clips.' + (' The video has no more distinct speech highlights at the current clip length. Existing clips are kept; suggestions do not overlap them.' if created < count else ' Review your clips, then render them to MP4.'),
    }
    p['requested_clip_count'] = count
    p['clip_generation'].update(selection_mode=p.get('selection_mode','quality'),minimum_score=p.get('minimum_score',70),auto_count=auto,min_duration=p.get('min_duration',8),max_duration=p.get('max_duration',60))
    if quality:
        p['clip_generation']['diagnostics']=diagnostics
        p['clip_generation']['message']=f"Created {created} of up to {count} clips above engagement score {p.get('minimum_score',70)}. "
        if shortfall:p['clip_generation']['message']+=shortfall+' '
        p['clip_generation']['message']+=f"Clip length: {p.get('min_duration',8):g}–{p.get('max_duration',60):g} seconds. Analysed {diagnostics['candidate_ranges']} candidate ranges: {diagnostics['below_score']} below the score rule, {diagnostics['passed_score']} passed it. "
        if not diagnostics['candidate_ranges']:
            p['clip_generation']['message']+='No complete speech range matched the duration and pause rules. Try a shorter minimum duration or a wider duration range. '
        overlaps=diagnostics['overlap_existing']+diagnostics['overlap_selected']
        duplicates=diagnostics['duplicate_existing']+diagnostics['duplicate_selected']
        if overlaps or duplicates:
            p['clip_generation']['message']+=f'Skipped {overlaps} overlapping and {duplicates} near-duplicate ranges. These are alternative ranges of moments, not additional exportable clips. '
        p['clip_generation']['message']+="The count is a maximum. Scores use transcript heuristics"+(' with measured audio/visual signals' if p.get('media_analysis') else '')+", not probabilities of views. Preview before downloading."
    elif shortfall:p['clip_generation']['message']+=' '+shortfall
    if auto:p['clip_generation']['message']='Auto quantity: '+p['clip_generation']['message']
    capacity=max(1,int(p['duration']//p.get('min_duration',8)))
    p['clip_generation']['duration_capacity']=capacity
    if not auto and count>capacity:
        p['clip_generation']['message']+=f" Duration limit: at most {capacity} non-overlapping clips of at least {p.get('min_duration',8):g} seconds fit in this source, before quality rules and pauses. Choose a shorter duration to request more."
    if p['duration']<p.get('min_duration',8):p['clip_generation']['message']+=' Short source: the minimum duration was reduced to its available length.'
    if empty_reason=='already_selected':
        p['clip_generation']['message']+=' Available moments are already covered by existing clips. Review those clips; clicking Generate again will not duplicate them.'
    elif empty_reason=='no_qualified_moments':
        p['clip_generation']['message']+=' No new moment passed these rules. Lower the minimum score or explicitly try Explore all suggestions.'
    elif empty_reason=='insufficient_material':
        p['clip_generation']['message']+=' Not enough distinct uncovered speech remains. Review existing clips or use a longer source.'

def render_generated_batch(project_id,batch_id):
    ids=[]
    def queue(p):
        for c in p['clips']:
            if c.get('batch_id')==batch_id and c['status']=='draft':
                c.update(status='queued',error=None);ids.append(c['id'])
    p=store.mutate(project_id,queue)
    for cid in ids:render_pool.submit(render_clip,project_id,cid)
    return p

def cleanup_deleted(folder):
    # A response may still hold a Windows file handle after its project is gone.
    # Tombstones cannot be served by any project/media API.
    for attempt in range(20):
        try:
            shutil.rmtree(folder)
            return
        except FileNotFoundError:
            return
        except OSError:
            if attempt==19:
                log.warning('Deferred project cleanup will retry at startup: %s',folder)
                return
            time.sleep(.25 if attempt<4 else 1)


def recover_deletions():
    for folder in store.DATA.glob('.deleted-*'):
        if not folder.is_dir() or folder.is_symlink():continue
        parts=folder.name[9:].rsplit('-',1)
        if len(parts)!=2 or len(parts[1])!=32 or any(c not in '0123456789abcdef' for c in parts[1]):continue
        project_id=parts[0]
        original=(store.DATA/project_id).resolve()
        if original.parent!=store.DATA.resolve():continue
        if store.get(project_id):
            # Crash before the SQLite commit: restore the still-owned project.
            if not original.exists():folder.rename(original)
        else:cleanup_pool.submit(cleanup_deleted,folder)


@asynccontextmanager
async def lifespan(app):
    guest.prepare_legacy()
    recover_deletions()
    platform.recover_studio()
    for job in store.all_imports():
        if job['status'] not in ('ready','error'):
            store.import_update(job['id'],status='error',error='Link import was interrupted. Retry the link or open the imported project if available.')
    for p in store.all_projects():
        if p['status'] in ('queued', 'transcribing', 'analyzing'):
            p.update(status='error', error='Processing was interrupted. Retry transcription to continue.')
        if p.get('dubbing',{}).get('status') in ('queued','rendering'):
            p['dubbing'].update(status='error',enabled=False,error='Voice translation was interrupted. Retry in Transcript.')
        for c in p['clips']:
            if c['status'] in ('queued', 'rendering'):
                c.update(status='error', error='Export was interrupted. Render again to continue.')
        store.save(p)
    yield

app = FastAPI(title='ClipForge AI', lifespan=lifespan, dependencies=[Depends(guest.authorize)])
assets.register_routes(app)
platform.register_routes(app)

@app.middleware('http')
async def local_origin(request: Request, call_next):
    origin = request.headers.get('origin')
    allowed = {'http://127.0.0.1:3000', 'http://localhost:3000', 'http://127.0.0.1:8000', 'http://localhost:8000'}
    allowed.update(value.strip() for value in os.environ.get('CLIPFORGE_ALLOWED_ORIGINS','').split(',') if value.strip())
    if request.url.path.startswith('/api/') and request.headers.get('sec-fetch-site') == 'cross-site':
        return JSONResponse({'detail':'Cross-site API requests are not allowed.'},status_code=403)
    if request.method not in ('GET', 'HEAD', 'OPTIONS') and origin and origin not in allowed:
        return JSONResponse({'detail': 'This local application does not accept requests from that origin.'}, status_code=403)
    response = await call_next(request)
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'private, no-store'
        response.headers['Vary'] = 'Cookie'
    return response

@app.get('/api/session')
def guest_session(request: Request, response: Response):
    return guest.bootstrap(request,response)

class LegacyClaim(BaseModel):
    key: str = Field(min_length=43,max_length=43)

@app.post('/api/session/claim-legacy')
def claim_previous_projects(options: LegacyClaim, request: Request):
    return guest.claim_legacy(options.key,request.state.owner_id)

def project_or_404(project_id):
    p = store.get(project_id)
    if not p:
        raise HTTPException(404, 'Project not found')
    return p

def directory(project_id):
    project_or_404(project_id)
    return store.DATA / project_id

def caption_conversion(segments,language,script):
    # Manually entered captions can have no detected speech language. Native
    # Hindi text can stay in its script, and supported Urdu/Devanagari text can
    # be romanized directly without pretending to detect/translate the audio.
    # A known unrelated language must still use the normal route checks below.
    if language in (None,'auto'):
        has_arabic=any(romanization.URDU.search(s['text']) for s in segments)
        has_devanagari=any(romanization.HINDI.search(s['text']) for s in segments)
        if script=='hindi' and has_devanagari and not has_arabic:
            return deepcopy(segments),script,None
        if script=='roman_urdu' and (has_arabic or has_devanagari):
            return romanization.convert_segments(segments,script),script,None
    # A stored Hindi pass can retain an older Urdu language label. Inspect only
    # the native script here; never relabel unrelated native languages as Urdu.
    if script=='hindi' and language in ('ur','hi') and not any(romanization.URDU.search(s['text']) for s in segments) and any(romanization.HINDI.search(s['text']) for s in segments):
        language='hi'
    if not translation.conversion_available(language,script):
        detected=SPEECH_NAMES.get(language,language or 'another language')
        warning=f'Detected {detected} speech. Local translation to {caption_name(script)} is unavailable because no installed model route supports this pair; clips use the original-language captions. Your requested language choice is saved. Native captions remain available; no spoken-audio dubbing is applied.'
        return deepcopy(segments),'original',warning
    return translation.convert_segments(segments,language,script),script,None


def convert_project_captions(project_id,segments,language,script):
    converted,effective,warning=caption_conversion(segments,language,script)
    def save(p):
        p.update(caption_warning=warning,caption_script=effective)
        if warning:p['requested_caption_script']=script
        else:p.pop('requested_caption_script',None)
    store.mutate(project_id,save)
    return converted


def process(project_id):
    try:
        p = project_or_404(project_id)
        if not p['has_audio']:
            raise ValueError('No audio stream found. You can still create clips manually.')
        store.mutate(project_id, lambda p: p.update(status='transcribing', error=None))
        global model
        with speech.timeline_audio(directory(project_id)/'source') as audio_source, model_lock:
            mode = p.get('transcription_mode','balanced')
            # Detect the source independently before selecting a large native
            # model. Choosing Punjabi output for English must not force Punjabi ASR.
            if model is None:
                model = models.get('base') or speech.load_model('base',store.DATA/'models')
                models['base']=model
            language,language_warning=speech.resolve_language(model,audio_source,p.get('speech_language','auto'))
            model_name = speech.model_name(mode,p.get('caption_script','original'),language or 'auto')
            separate_model=model_name!='base'
            if not separate_model and model is not None:
                recognizer = model
            elif model_name in models:
                recognizer = models[model_name]
            else:
                recognizer = speech.load_model(model_name,store.DATA/'models')
                models[model_name] = recognizer
                if not separate_model:
                    model = recognizer
            store.mutate(project_id,lambda project:project.update(speech_warning=language_warning,recognized_speech_language=language))
            if not language:
                segments, info = speech.transcribe(recognizer,audio_source,mode,caption_script=p.get('caption_script','original'))
            else:
                segments, info = speech.transcribe(recognizer,audio_source,mode,language=language,caption_script=p.get('caption_script','original'))
            transcript = []
            updated_at = time.monotonic()
            for i,s in enumerate(segments):
                if s.end > s.start and s.start < p['duration']:
                    speech.validate_text(s.text)
                    transcript.append({'id':i,'start':round(s.start,3),'end':round(min(s.end,p['duration']),3),'text':s.text.strip()})
                    transcript[-1]['words']=[{'word':w.word,'start':round(max(s.start,w.start),3),'end':round(min(w.end,s.end,p['duration']),3)} for w in (getattr(s,'words',None) or []) if w.end>w.start and w.start<p['duration']]
                if time.monotonic()-updated_at >= 2:
                    store.mutate(project_id, lambda project:project.update(transcription_progress=min(99,round(s.end/p['duration']*100))))
                    updated_at = time.monotonic()
        source_transcript=deepcopy(transcript)
        store.mutate(project_id,lambda project:project.update(processing_message='Preparing subtitle language / translation…',source_transcript=source_transcript,language=info.language))
        transcript=convert_project_captions(project_id,transcript,info.language,p.get('caption_script','original'))
        store.mutate(project_id, lambda p: p.update(status='analyzing', transcript=transcript, source_transcript=source_transcript, language=info.language))
        prepare_analysis(project_id)
        def finish(p):
            p.update(status='ready', transcript=transcript, language=info.language, transcription_progress=100,processing_message=None)
            realign=p.pop('realign_existing',False)
            regenerate=p.pop('generate_after_redo',False)
            if realign:
                for c in p['clips']:
                    c.update(status='draft',file=None,error=None)
                    selection.invalidate(c)
            if not realign or regenerate:
                add_highlights(p, p.get('requested_clip_count', 5))
        completed=store.mutate(project_id, finish)
        if completed.get('auto_render_generated'):
            render_generated_batch(project_id,completed.get('clip_generation',{}).get('batch_id'))
    except Exception as exc:
        log.exception('Transcription failed')
        store.mutate(project_id, lambda p: p.update(status='error', error=str(exc)))

def render_clip(project_id, clip_id):
    try:
        def begin(p):
            next(c for c in p['clips'] if c['id'] == clip_id).update(status='rendering', error=None)
        p = store.mutate(project_id, begin)
        c = next(c for c in p['clips'] if c['id'] == clip_id)
        folder = directory(project_id)
        filename = f"{clip_id}-{uuid.uuid4().hex[:8]}.{c.get('output_format','mp4')}"
        dubbed_audio=dubbing.audio_for_project(p,folder)
        media.render(folder / 'source', folder, c, p['transcript'], folder / filename,assets=p.get('assets',[]),**({'audio_source':dubbed_audio} if dubbed_audio else {}))
        def done(p):
            next(c for c in p['clips'] if c['id'] == clip_id).update(status='ready', file=filename)
        store.mutate(project_id, done)
    except Exception as exc:
        log.exception('Render failed')
        def fail(p):
            next(c for c in p['clips'] if c['id'] == clip_id).update(status='error', error=str(exc))
        store.mutate(project_id, fail)

@app.get('/api/health')
def health():
    return {'status': 'ok', 'ffmpeg': bool(media.FFMPEG), 'model': os.environ.get('WHISPER_MODEL', 'base'), 'model_loaded': model is not None, 'render_workers':RENDER_WORKERS}


@app.get('/api/languages')
def language_capabilities():
    return capability_catalog()


@app.get('/api/sound-effects/{name}')
def sound_effect_preview(name:Literal[*compositor.SOUNDS]):
    folder=store.DATA/'sound-effects'
    folder.mkdir(exist_ok=True)
    path=folder/(name+'.wav')
    if not path.is_file():
        temporary=folder/(name+'-'+uuid.uuid4().hex+'.wav')
        try:
            media.run(['-f','lavfi','-i',compositor.SOUNDS[name],'-ac','1','-c:a','pcm_s16le',str(temporary)],timeout=15)
            if not path.is_file():temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
    return FileResponse(path,media_type='audio/wav',content_disposition_type='inline')


@app.get('/api/discover/{video_id}/thumbnail')
def discovery_thumbnail(video_id:str):
    return Response(thumbnails.fetch_image(video_id),media_type='image/jpeg')


@app.get('/api/projects/{project_id}/dubbing/capabilities')
def dubbing_capabilities(project_id:str):
    return dubbing.catalog(project_or_404(project_id).get('language'))


class DubbingInput(BaseModel):
    caption_script: CaptionScript = 'english'
    enabled: bool = True
    auto_render: bool = False


def invalidate_exports(p):
    dub=p.get('dubbing',{})
    if dub.get('enabled') and dub.get('fingerprint')!=dubbing.fingerprint(p['transcript'],dub.get('language')):
        dub.update(status='stale',error='Captions changed. Generate the translated voice again to match the edited words and timing, or use original audio.')
    for clip in p['clips']:
        clip.update(status='draft',file=None,error=None)
        selection.invalidate(clip)


def run_dubbing(project_id,options,snapshot):
    folder=directory(project_id)
    filename='dub-'+uuid.uuid4().hex+'.wav'
    output=folder/filename
    video=output.with_suffix('.mp4')
    try:
        target=CAPTION_TARGETS[options.caption_script]
        native_script='urdu' if options.caption_script=='roman_urdu' else options.caption_script
        groups=dubbing.sentence_groups(snapshot['source_transcript'])
        engine_name='m2m100-v1' if translation.multilingual.installed(translation.ROOT) else 'argos-v1'
        cache=folder/('dub-text-'+dubbing.fingerprint(groups,snapshot['language']+'>'+target+'|'+engine_name)+'.json')
        if cache.is_file():
            native=json.loads(cache.read_text(encoding='utf-8'))
        else:
            def translation_progress(done,total):
                store.mutate(project_id,lambda p:p.update(processing_message=f'Translating captions: {done} / {total} sentences'))
            native=translation.convert_segments(groups,snapshot['language'],native_script,progress=translation_progress)
            cache.write_text(json.dumps(native,ensure_ascii=False),encoding='utf-8')
        last_update=[0]
        def progress(done,total):
            if time.monotonic()-last_update[0]>1 or done==total:
                store.mutate(project_id,lambda p:p.update(processing_message=f'Preparing translated voice: {done} / {total} sentences'))
                last_update[0]=time.monotonic()
        dubbing.create_track(native,target,snapshot['duration'],output,progress)
        transcript=romanization.convert_segments(native,'roman_urdu') if options.caption_script=='roman_urdu' else native
        for segment in transcript:
            segment.pop('words',None)
            segment['timing']='dubbed_sentence'
        store.mutate(project_id,lambda p:p.update(processing_message='Preparing playable translated video…'))
        dubbing.create_video(folder/'source',output,video,snapshot['duration'])
        def finish(p):
            if not p.get('source_transcript') and snapshot['language']==p.get('language'):
                p['source_transcript']=deepcopy(snapshot['source_transcript'])
            p.update(status='ready',error=None,processing_message=None,transcript=transcript,
                     caption_script=options.caption_script,caption_warning=None,dubbing_error=None)
            p.pop('requested_caption_script',None)
            p['dubbing']={'enabled':True,'status':'ready','language':target,'caption_script':options.caption_script,
                          'file':filename,'video_file':video.name,'engine':'eSpeak NG','mouth_animation':False,
                          'fingerprint':dubbing.fingerprint(transcript,target)}
            invalidate_exports(p)
        p=store.mutate(project_id,finish)
    except Exception as exc:
        output.unlink(missing_ok=True)
        video.unlink(missing_ok=True)
        log.exception('Offline dubbing failed')
        store.mutate(project_id,lambda p:p.update(status='ready',processing_message=None,
                     dubbing_error=str(exc),dubbing=snapshot.get('dubbing',{})))
        return
    if options.auto_render and p['clips']:
        render_all_clips(project_id)


@app.post('/api/projects/{project_id}/dubbing',status_code=202)
def translate_voice(project_id:str,options:DubbingInput):
    current=project_or_404(project_id)
    snapshot=deepcopy(current)
    if options.enabled:
        target=CAPTION_TARGETS.get(options.caption_script)
        # Honor edits to text already in the requested output language. A saved
        # translated transcript is not evidence that the original audio spoke it.
        current_language=CAPTION_TARGETS.get(current.get('caption_script')) or current.get('language')
        if current.get('transcript') and (current_language==target or not current.get('source_transcript')) and current.get('caption_script')!='roman_urdu':
            snapshot.update(source_transcript=deepcopy(current['transcript']),language=current_language)
        if not snapshot.get('source_transcript') or not snapshot.get('language'):
            raise HTTPException(400,'Re-transcribe the actual source audio first. Dubbing requires saved original-language speech and timestamps.')
        try:
            for segment in snapshot['source_transcript']:speech.validate_text(segment['text'])
        except ValueError as exc:
            raise HTTPException(400,str(exc)) from exc
        if not target or not translation.route_available(snapshot['language'],target):
            raise HTTPException(400,'No installed translation model supports this language pair. Your current captions and source audio were kept.')
        if target not in dubbing.voices():
            raise HTTPException(400,'No installed offline voice supports this language. Run python -m backend.scripts.setup_dubbing or choose another language.')
    def claim(p):
        if p['status'] in ('queued','transcribing','analyzing') or any(c['status'] in ('queued','rendering') for c in p['clips']):
            raise HTTPException(409,'Wait for the current job to finish.')
        if options.enabled and (p['transcript']!=current['transcript'] or p.get('language')!=current.get('language') or p.get('caption_script')!=current.get('caption_script')):
            raise HTTPException(409,'Caption language or text changed. Reload the project before translating the voice.')
        if not options.enabled:
            if p.get('dubbing',{}).get('enabled'):
                p['dubbing'].update(enabled=False,error=None)
                invalidate_exports(p)
            p['dubbing_error']=None
        else:
            p.update(status='analyzing',dubbing_error=None,processing_message='Translating saved speech and preparing an offline voice…')
            p['dubbing']={**p.get('dubbing',{}),'status':'rendering','enabled':False}
    queued=store.mutate(project_id,claim)
    if options.enabled:
        pool.submit(run_dubbing,project_id,options,snapshot)
    return queued


@app.get('/api/projects/{project_id}/dubbing/audio')
def dubbing_audio(project_id:str):
    p=project_or_404(project_id)
    try:
        path=dubbing.audio_for_project(p,directory(project_id))
    except ValueError as exc:
        raise HTTPException(409,str(exc)) from exc
    if not path:
        raise HTTPException(404,'No translated voice is enabled.')
    return FileResponse(path,media_type='audio/wav',content_disposition_type='inline')


@app.get('/api/projects/{project_id}/dubbing/video')
def dubbing_video(project_id:str):
    p=project_or_404(project_id)
    folder=directory(project_id)
    try:
        audio=dubbing.audio_for_project(p,folder)
    except ValueError as exc:
        raise HTTPException(409,str(exc)) from exc
    filename=p.get('dubbing',{}).get('video_file')
    if not audio or not filename:raise HTTPException(404,'No translated video is ready. Generate the translated voice first.')
    path=(folder/filename).resolve()
    if path.parent!=folder.resolve() or not path.is_file():raise HTTPException(404,'Translated video is missing. Regenerate the translated voice.')
    return FileResponse(path,media_type='video/mp4',filename='zyntracut-translated.mp4',content_disposition_type='inline')

@app.get('/api/projects')
def projects(request: Request):
    return [p for p in store.all_projects() if p.get('owner_id') == request.state.owner_id]

@app.get('/api/projects/{project_id}')
def project(project_id: str):
    return project_or_404(project_id)

@app.get('/api/projects/{project_id}/subtitles')
def download_subtitles(project_id: str, format: Literal['srt','vtt']='srt', clip_id: str | None=None):
    p=project_or_404(project_id)
    start,end=0,p['duration']
    speed=1
    offset=0
    if clip_id:
        c=next((c for c in p['clips'] if c['id']==clip_id),None)
        if not c:
            raise HTTPException(404,'Clip not found')
        start,end=c['start'],c['end']
        speed=c.get('speed',1)
        offset=c.get('caption_offset',0)
    text=media.subtitle_file(p['transcript'],format,start,end,speed,offset)
    return Response(text,media_type='text/vtt' if format=='vtt' else 'application/x-subrip',headers={'Content-Disposition':f'attachment; filename="clipforge-subtitles.{format}"'})

@app.delete('/api/projects/{project_id}', status_code=204)
def delete_project(project_id: str):
    original=quarantine=None
    try:
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            p = project_or_404(project_id)
            if p['status'] in ('queued', 'transcribing', 'analyzing') or any(c['status'] in ('queued', 'rendering') for c in p['clips']) or any(job.get('project_id')==project_id and job['status'] not in ('ready','error') for job in store.all_imports()):
                raise HTTPException(409, 'Wait for processing to finish before deleting a project.')
            original=(store.DATA/project_id).resolve()
            if original.parent!=store.DATA.resolve():
                raise HTTPException(400,'Invalid project path')
            if original.exists():
                quarantine=store.DATA/('.deleted-'+project_id+'-'+uuid.uuid4().hex)
                try:original.rename(quarantine)
                except OSError as exc:
                    quarantine=None
                    raise HTTPException(409,'Close this video in other players and retry deletion. Your project is still available.') from exc
            db.execute('DELETE FROM projects WHERE id=?',(project_id,))
            for job_id,payload in list(db.execute('SELECT id,payload FROM imports')):
                if json.loads(payload).get('project_id')==project_id:
                    db.execute('DELETE FROM imports WHERE id=?',(job_id,))
    except Exception:
        if quarantine and quarantine.exists():quarantine.rename(original)
        raise
    if quarantine:
        try:shutil.rmtree(quarantine)
        except OSError:cleanup_pool.submit(cleanup_deleted,quarantine)

@app.delete('/api/projects/{project_id}/clips/{clip_id}', status_code=204)
def delete_clip(project_id: str, clip_id: str):
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        p = project_or_404(project_id)
        if p['status'] in ('queued','transcribing','analyzing') or any(c['status'] in ('queued','rendering') for c in p['clips']) or any(job.get('project_id')==project_id and job['status'] not in ('ready','error') for job in store.all_imports()):
            raise HTTPException(409,'Wait for processing to finish before deleting a clip.')
        c = next((c for c in p['clips'] if c['id']==clip_id),None)
        if not c:
            raise HTTPException(404,'Clip not found')
        folder = (store.DATA/project_id).resolve()
        if folder.parent != store.DATA.resolve():
            raise HTTPException(400,'Invalid project path')
        # All revisions and ASS files for this clip; never touch source/siblings.
        files = [item for item in folder.iterdir() if item.is_file() and item.name.startswith(clip_id+'-') and item.suffix in ('.mp4','.webm','.ass')] if folder.exists() else []
        if c.get('file'):
            files.sort(key=lambda item:item.name!=c['file'])
        try:
            for item in files:
                item.unlink(missing_ok=True)
        except PermissionError as exc:
            raise HTTPException(409,'Close this clip in other players and retry deletion.') from exc
        p['clips'] = [item for item in p['clips'] if item['id']!=clip_id]
        db.execute('UPDATE projects SET payload=? WHERE id=?',(json.dumps(p),project_id))

@app.post('/api/projects', status_code=201)
def upload(file: UploadFile, request: Request):
    project_id = uuid.uuid4().hex
    folder = store.DATA / project_id
    folder.mkdir()
    source = folder / 'source'
    try:
        size = 0
        with source.open('wb') as target:
            while chunk := file.file.read(1024 * 1024):
                size += len(chunk)
                if size > 2 * 1024**3:
                    raise HTTPException(413, 'Maximum upload size is 2 GB.')
                target.write(chunk)
        info = media.probe(source)
        p = {'id': project_id, 'name': (file.filename or 'Untitled video')[:200], 'created_at': datetime.now(timezone.utc).isoformat(), 'size': size, **info, 'status': 'uploaded', 'error': None, 'language': None, 'transcript': [], 'clips': []}
        p['owner_id'] = request.state.owner_id
        try:
            media.run(['-ss', str(min(1, info['duration']/2)), '-i', str(source), '-frames:v', '1', '-vf', 'scale=640:-2', str(folder / 'poster.jpg')], timeout=30)
        except Exception:
            log.warning('Could not create poster', exc_info=True)
        store.save(p)
        return p
    except Exception as exc:
        for item in folder.iterdir():
            item.unlink(missing_ok=True)
        folder.rmdir()
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(400, f'Could not read video: {exc}') from exc
    finally:
        file.file.close()

def queue_transcription(project_id,options,generate_after_redo=False):
    def queue(p):
        assets.validate_references(p,options.generated_settings or {})
        if p['status'] in ('queued', 'transcribing', 'analyzing') or any(c['status'] in ('queued', 'rendering') for c in p['clips']):
            raise HTTPException(409, 'Wait for the current job to finish.')
        if p['transcript'] and not options.redo:
            raise HTTPException(409, 'This project already has a transcript. Edit it in the transcript panel.')
        p['realign_existing']=bool(options.redo and p['transcript'])
        if options.redo and p['transcript']:
            p['transcript_history']=[*p.get('transcript_history',[]),
                {'created_at':datetime.now(timezone.utc).isoformat(),'language':p.get('language'),
                 'caption_script':p.get('caption_script','original'),'transcript':deepcopy(p['transcript']),
                 'source_transcript':deepcopy(p.get('source_transcript',p['transcript']))}][-3:]
        p['generate_after_redo']=generate_after_redo
        p['auto_render_generated']=options.auto_render and (generate_after_redo or not p['realign_existing'])
        if options.generated_settings is not None:p['default_effects']=options.generated_settings
        if p.get('dubbing',{}).get('enabled'):
            p['dubbing'].update(enabled=False,error='Source speech is being replaced. Regenerate the translated voice afterwards.')
        p.update(status='queued', error=None, requested_clip_count=options.clip_count, auto_count=options.auto_count,min_duration=options.min_duration,max_duration=options.max_duration, transcription_mode=options.transcription_mode, speech_language=options.speech_language, caption_script=options.caption_script, transcription_progress=0,selection_mode=options.selection_mode,minimum_score=options.minimum_score)
    p = store.mutate(project_id, queue)
    if not p:
        raise HTTPException(404, 'Project not found')
    pool.submit(process, project_id)
    return p

@app.post('/api/projects/{project_id}/transcribe', status_code=202)
def transcribe(project_id: str, options: GenerationInput | None = None):
    return queue_transcription(project_id,options or GenerationInput())


class RecoveryOptions(BaseModel):
    selection_mode: Literal['quality','all']|None=None
    minimum_score:int|None=Field(default=None,ge=0,le=100,strict=True)


def recovery_source(project_id):
    folder=(store.DATA/project_id).resolve()
    source=folder/'source'
    if folder.parent!=store.DATA.resolve() or source.resolve().parent!=folder:
        raise HTTPException(400,'Invalid project source path.')
    if not source.is_file() or not source.stat().st_size:
        raise HTTPException(400,'The downloaded source video is unavailable. Upload the video again before generating previews.')
    return source


def recover_saved_speech(project_id):
    try:
        recovery_source(project_id)
        def finish(p):
            requested=p.get('caption_script','original')
            if requested!='original':p['requested_caption_script']=requested
            p.update(transcript=deepcopy(p['source_transcript']),caption_script='original',status='ready',error=None,transcription_progress=100,processing_message=None,
                     caption_warning='Recovered saved original-language speech. No video download or speech recognition was repeated; unsupported translation was not applied.')
            add_highlights(p,p.get('requested_clip_count',5))
        p=store.mutate(project_id,finish)
        render_generated_batch(project_id,p['clip_generation']['batch_id'])
        for job in store.all_imports():
            if job.get('project_id')==project_id:
                store.import_update(job['id'],status='ready',error=None,message='Saved speech recovered. Open this video to review clip generation and previews.')
    except Exception as exc:
        log.exception('Saved transcript recovery failed')
        store.mutate(project_id,lambda p:p.update(status='error',error=str(exc),processing_message=None))
        for job in store.all_imports():
            if job.get('project_id')==project_id:
                store.import_update(job['id'],status='error',error=str(exc),message='Saved speech recovery needs attention. Your project is kept.')


@app.post('/api/projects/{project_id}/recover',status_code=202)
def recover_project(project_id:str,options:RecoveryOptions|None=None):
    def claim(p):
        if p['status'] in ('queued','transcribing','analyzing') or any(c['status'] in ('queued','rendering') for c in p['clips']) or any(job.get('project_id')==project_id and job['status'] not in ('ready','error') for job in store.all_imports()):raise HTTPException(409,'Wait for current processing to finish.')
        if not p.get('source_transcript'):raise HTTPException(400,'No saved source transcript is available. Retry transcription using Original subtitles.')
        recovery_source(project_id)
        if options:
            p.update({k:v for k,v in options.model_dump().items() if v is not None})
        p.update(status='analyzing',error=None,processing_message='Recovering saved speech and preparing clips; no download or transcription repeat.')
    p=store.mutate(project_id,claim)
    if not p:raise HTTPException(404,'Project not found')
    pool.submit(recover_saved_speech,project_id)
    return p

@app.post('/api/projects/{project_id}/highlights')
def generate_highlights(project_id: str, options: GenerationInput):
    current=project_or_404(project_id)
    assets.validate_references(current,options.generated_settings or {})
    if needs_output_transcription(current,options.caption_script):
        return JSONResponse(status_code=202,content=queue_transcription(project_id,options.model_copy(update={'redo':True}),generate_after_redo=True))
    def claim(p):
        if p['status'] in ('queued','transcribing','analyzing') or any(c['status'] in ('queued','rendering') for c in p['clips']):
            raise HTTPException(409,'Wait for the current job to finish.')
        if not p['transcript']:
            raise HTTPException(400,'Transcribe your video or add subtitles before generating highlights.')
        p.update(status='analyzing',error=None,processing_message='Measuring source signals and ranking highlights…')
    queued=store.mutate(project_id,claim)
    if options.background:
        pool.submit(run_saved_generation,project_id,options,current['status'])
        return JSONResponse(status_code=202,content=queued)
    return finish_saved_generation(project_id,options,current['status'])


def run_saved_generation(project_id,options,previous_status):
    try:
        finish_saved_generation(project_id,options,previous_status)
    except Exception as exc:
        log.exception('Highlight generation failed')
        detail=exc.detail if isinstance(exc,HTTPException) else str(exc)
        store.mutate(project_id,lambda p:p.update(status='error',error=str(detail),processing_message=None))


def finish_saved_generation(project_id,options,previous_status):
    prepare_analysis(project_id)
    def generate(p):
        if not p['transcript']:
            raise HTTPException(400, 'Transcribe your video or add subtitles before generating highlights.')
        if 'caption_script' in options.model_fields_set:
            set_transcript_script(p,options.caption_script)
        p.update(selection_mode=options.selection_mode,minimum_score=options.minimum_score,auto_count=options.auto_count,min_duration=options.min_duration,max_duration=options.max_duration,processing_message=None,status='ready')
        if options.generated_settings is not None:p['default_effects']=options.generated_settings
        add_highlights(p, options.clip_count)
    try:
        p = store.mutate(project_id, generate)
    except Exception:
        store.mutate(project_id,lambda p:p.update(status=previous_status,processing_message=None))
        raise
    if not p:
        raise HTTPException(404, 'Project not found')
    if options.auto_render:p=render_generated_batch(project_id,p['clip_generation']['batch_id'])
    return p

@app.post('/api/projects/{project_id}/clips/render', status_code=202)
def render_all_clips(project_id: str):
    clip_ids = []
    def queue(p):
        if p['status'] in ('queued', 'transcribing', 'analyzing') or any(c['status'] in ('queued', 'rendering') for c in p['clips']):
            raise HTTPException(409, 'Wait for the current job to finish.')
        for c in p['clips']:
            if c['status'] in ('draft', 'error'):
                c.update(status='queued', error=None)
                clip_ids.append(c['id'])
        if not clip_ids:
            raise HTTPException(400, 'No draft clips to render. Generate clips first.')
    p = store.mutate(project_id, queue)
    if not p:
        raise HTTPException(404, 'Project not found')
    for clip_id in clip_ids:
        render_pool.submit(render_clip, project_id, clip_id)
    return p

class Segment(BaseModel):
    id: int
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    text: str = Field(max_length=2000)


def needs_hindi_transcription(p):
    if p.get('caption_script')=='hindi':
        return False
    source=p.get('source_transcript',p['transcript'])
    return any(romanization.URDU.search(s['text']) for s in source) or (p.get('caption_script')=='roman_urdu' and 'source_transcript' not in p)


def needs_output_transcription(p,script):
    if script==p.get('caption_script','original'):return False
    source=p.get('source_transcript',p['transcript'])
    if script=='hindi' and p.get('language') in (None,'ur','hi'):return needs_hindi_transcription(p)
    if script=='urdu' and p.get('language') in ('ur','hi'):return any(romanization.HINDI.search(s['text']) for s in source)
    return False


def set_transcript_script(p,script):
    if script==p.get('caption_script','original'):
        return
    previous=deepcopy(p['transcript'])
    if script=='original':
        if 'source_transcript' not in p:
            raise HTTPException(400,'Original-script text is unavailable after manual edits. Re-transcribe to recover it.')
        p['transcript']=deepcopy(p['source_transcript'])
        p.update(caption_warning=None)
        p.pop('requested_caption_script',None)
        effective=script
    else:
        if 'source_transcript' not in p:
            p['source_transcript']=deepcopy(p['transcript'])
        converted,effective,warning=caption_conversion(p['source_transcript'],p.get('language'),script)
        p['transcript']=converted
        p['caption_warning']=warning
        if warning:p['requested_caption_script']=script
        else:p.pop('requested_caption_script',None)
    p['caption_script']=effective
    if p['transcript']!=previous:
        invalidate_exports(p)


class TranscriptScriptInput(BaseModel):
    caption_script: CaptionScript


@app.post('/api/projects/{project_id}/transcript/script')
def change_transcript_script(project_id: str, options: TranscriptScriptInput):
    current=project_or_404(project_id)
    if needs_output_transcription(current,options.caption_script):
        settings=GenerationInput(redo=True,caption_script=options.caption_script,transcription_mode='accurate',speech_language=current.get('speech_language','auto'))
        return JSONResponse(status_code=202,content=queue_transcription(project_id,settings))
    def update(p):
        if p['status'] in ('queued','transcribing','analyzing') or any(c['status'] in ('queued','rendering') for c in p['clips']):
            raise HTTPException(409,'Wait for processing to finish before changing subtitle script.')
        if not p['transcript']:
            raise HTTPException(400,'Transcribe the video first.')
        set_transcript_script(p,options.caption_script)
    p=store.mutate(project_id,update)
    if not p:
        raise HTTPException(404,'Project not found')
    return p

@app.put('/api/projects/{project_id}/transcript')
def save_transcript(project_id: str, segments: list[Segment]):
    if len(segments) > 20000:
        raise HTTPException(400, 'Too many segments')
    def update(p):
        if p['status'] in ('queued', 'transcribing', 'analyzing') or any(c['status'] in ('queued', 'rendering') for c in p['clips']):
            raise HTTPException(409, 'Wait for processing to finish before editing subtitles.')
        if len({s.id for s in segments}) != len(segments) or any(s.end <= s.start or s.end > p['duration'] + .05 for s in segments):
            raise HTTPException(400, 'Invalid subtitle timing or duplicate IDs')
        previous={s['id']:s for s in p['transcript']}
        p['transcript'] = [s.model_dump() for s in sorted(segments, key=lambda s: s.start)]
        if len(previous)!=len(segments) or any(any(previous.get(s['id'],{}).get(k)!=s[k] for k in ('text','start','end')) for s in p['transcript']):
            # Never silently restore an obsolete snapshot over subsequent edits.
            p.pop('source_transcript',None)
        for s in p['transcript']:
            old=previous.get(s['id'],{})
            if all(old.get(k)==s[k] for k in ('text','start','end')) and old.get('words'):
                s['words']=old['words']
        invalidate_exports(p)
    p = store.mutate(project_id, update)
    if not p:
        raise HTTPException(404, 'Project not found')
    return p

class EffectSettings(BaseModel):
    image_asset_id: str|None = Field(default=None,pattern=r'^[a-f0-9]{32}$')
    image_start: float = Field(default=0,ge=0,le=600,allow_inf_nan=False)
    image_end: float = Field(default=3,gt=0,le=600,allow_inf_nan=False)
    image_layout: Literal['overlay','full'] = 'overlay'
    image_fit: Literal['contain','cover'] = 'contain'
    image_opacity: float = Field(default=1,ge=0,le=1,allow_inf_nan=False)
    image_width: float = Field(default=35,ge=3,le=100,allow_inf_nan=False)
    image_x: float = Field(default=50,ge=0,le=100,allow_inf_nan=False)
    image_y: float = Field(default=50,ge=0,le=100,allow_inf_nan=False)
    caption_offset: float = Field(default=0,ge=-5,le=5,allow_inf_nan=False)
    watermark_enabled: bool = False
    watermark_text: str = Field(default='',max_length=120)
    watermark_opacity: float = Field(default=.18,ge=0,le=1,allow_inf_nan=False)
    watermark_size: int = Field(default=72,ge=18,le=180)
    watermark_color: str = Field(default='#ffffff',pattern=r'^#[0-9a-fA-F]{6}$')
    watermark_x: float = Field(default=50,ge=0,le=100,allow_inf_nan=False)
    watermark_y: float = Field(default=50,ge=0,le=100,allow_inf_nan=False)
    logo_asset_id: str|None = Field(default=None,pattern=r'^[a-f0-9]{32}$')
    logo_opacity: float = Field(default=.4,ge=0,le=1,allow_inf_nan=False)
    logo_width: float = Field(default=18,ge=3,le=60,allow_inf_nan=False)
    logo_x: float = Field(default=90,ge=0,le=100,allow_inf_nan=False)
    logo_y: float = Field(default=10,ge=0,le=100,allow_inf_nan=False)
    filler_asset_id: str|None = Field(default=None,pattern=r'^[a-f0-9]{32}$')
    filler_start: float = Field(default=0,ge=0,le=600,allow_inf_nan=False)
    filler_end: float = Field(default=3,gt=0,le=600,allow_inf_nan=False)
    filler_layout: Literal['full','pip'] = 'full'
    music_asset_id: str|None = Field(default=None,pattern=r'^[a-f0-9]{32}$')
    music_volume: float = Field(default=.15,ge=0,le=1,allow_inf_nan=False)
    sound_effect: Literal['none',*compositor.SOUNDS] = 'none'
    sound_at: float = Field(default=0,ge=0,le=600,allow_inf_nan=False)
    sound_volume: float = Field(default=.5,ge=0,le=1,allow_inf_nan=False)
    transition: Literal['none','fade','white'] = 'none'
    transition_duration: float = Field(default=.35,ge=.1,le=2,allow_inf_nan=False)
    speed: float = Field(default=1,ge=1,le=4,allow_inf_nan=False)
    hide_webcam: bool = False
    webcam_x: float = Field(default=75,ge=0,le=99,allow_inf_nan=False)
    webcam_y: float = Field(default=0,ge=0,le=99,allow_inf_nan=False)
    webcam_width: float = Field(default=25,ge=1,le=100,allow_inf_nan=False)
    webcam_height: float = Field(default=35,ge=1,le=100,allow_inf_nan=False)
    aspect: Literal['vertical','square','original','landscape','portrait'] = 'original'
    framing: Literal['fit','crop'] = 'fit'
    crop_x: float = Field(default=50,ge=0,le=100,allow_inf_nan=False)
    crop_y: float = Field(default=50,ge=0,le=100,allow_inf_nan=False)
    style: Literal['mint','clean','yellow','boxed','neon','neon_highlight','minimal','cyan','orange','red','comic','elegant','shadow','none'] = 'mint'
    voice_effect: Literal['none','deep','high','radio','echo','mute'] = 'none'
    video_effect: Literal['none','vivid','warm','cool','mono','vintage','mirror','cinematic','sepia','soft','sharpen','blur'] = 'none'
    render_quality: Literal['fast','standard','high'] = 'high'
    output_format: Literal['mp4','webm'] = 'mp4'
    subtitle_font: Literal['Arial','Impact','Georgia','Anton','Bebas Neue','Poppins','Righteous','Bangers','Lobster','Pacifico','Kalam'] = 'Poppins'
    subtitle_size: int = Field(default=56,ge=18,le=96)
    caption_mode: Literal['phrase','karaoke','word'] = 'karaoke'
    caption_animation: Literal['none','pop','bounce','scale','fade'] = 'pop'
    highlight_color: str = Field(default='#ffdf35',pattern=r'^#[0-9a-fA-F]{6}$')
    audio_leveling: bool = False
    denoise: bool = False
    zoom: Literal['none','gentle','punch'] = 'none'
    sticker_enabled: bool = False
    subtitle_color: str | None = Field(default=None,pattern=r'^#[0-9a-fA-F]{6}$')
    subtitle_position: Literal['top','center','bottom'] = 'bottom'
    subtitle_uppercase: bool = False
    overlay_text: str = Field(default='',max_length=160)
    overlay_position: Literal['top','center','bottom'] = 'top'
    sticker: Literal['none','subscribe','follow','like'] = 'none'
    sticker_position: Literal['top-left','top-right','bottom-left','bottom-right'] = 'top-right'
    sticker_size: int = Field(default=30,ge=18,le=72)
    sticker_timing: Literal['full','start','middle','end','custom'] = 'full'
    sticker_animation: Literal['none','pop','fade','slide'] = 'none'
    sticker_duration: float = Field(default=3,ge=.2,le=60,allow_inf_nan=False)
    sticker_at: float = Field(default=0,ge=0,le=600,allow_inf_nan=False)
    voice_strength: float = Field(default=1,ge=0,le=1,allow_inf_nan=False)
    cover_source_captions: bool = False
    source_caption_y: float = Field(default=75,ge=0,le=99,allow_inf_nan=False)
    source_caption_height: float = Field(default=25,ge=1,le=100,allow_inf_nan=False)

    @model_validator(mode='after')
    def webcam_bounds(self):
        if self.image_end<=self.image_start:raise ValueError('Photo end must be after its start.')
        if self.filler_end<=self.filler_start:raise ValueError('B-roll end must be after its start.')
        if self.source_caption_y+self.source_caption_height>100:
            raise ValueError('Source caption cover must stay inside the video.')
        if self.webcam_x+self.webcam_width>100 or self.webcam_y+self.webcam_height>100:
            raise ValueError('Webcam cover must stay within the source frame.')
        return self

class ClipInput(EffectSettings):
    title: str = Field(min_length=1, max_length=160)
    start: float = Field(ge=0)
    end: float = Field(gt=0)

@app.put('/api/projects/{project_id}/clips/settings')
def apply_settings(project_id: str, settings: EffectSettings, include_ready: bool = False):
    def apply(p):
        assets.validate_references(p,settings.model_dump())
        if p['status'] in ('queued','transcribing','analyzing') or any(c['status'] in ('queued','rendering') for c in p['clips']):
            raise HTTPException(409,'Wait for processing to finish before applying effects.')
        targets = [c for c in p['clips'] if c['status'] in (('draft','error','ready') if include_ready else ('draft','error'))]
        if not targets:
            raise HTTPException(400,'There are no draft clips. Save a clip as a draft or generate new clips first.')
        for c in targets:
            if settings.image_asset_id and settings.image_start>=(c['end']-c['start'])/settings.speed:
                raise HTTPException(400,'Photo must start before the end of every target clip.')
            if settings.filler_asset_id and settings.filler_start>=(c['end']-c['start'])/settings.speed:
                raise HTTPException(400,'B-roll must start before the end of every target clip.')
            if settings.sound_effect!='none' and settings.sound_at>=(c['end']-c['start'])/settings.speed:
                raise HTTPException(400,'Sound effect must start before the end of every target clip.')
            if settings.sticker_enabled and settings.sticker!='none' and settings.sticker_timing=='custom' and settings.sticker_at>=(c['end']-c['start'])/settings.speed:
                raise HTTPException(400,'Sticker start must be before the end of every target clip. Use start/middle/end timing for mixed clip lengths.')
            c.update(**settings.model_dump(),status='draft',file=None,error=None)
    p = store.mutate(project_id,apply)
    if not p:
        raise HTTPException(404,'Project not found')
    return p

def validate_clip(clip, p):
    assets.validate_references(p,clip.model_dump())
    if clip.image_asset_id and clip.image_start>=(clip.end-clip.start)/clip.speed:
        raise HTTPException(400,'Photo must start before the output clip ends.')
    if clip.filler_asset_id and clip.filler_start>=(clip.end-clip.start)/clip.speed:
        raise HTTPException(400,'B-roll must start before the output clip ends.')
    if clip.sound_effect!='none' and clip.sound_at>=(clip.end-clip.start)/clip.speed:
        raise HTTPException(400,'Sound effect must start before the output clip ends.')
    if clip.end <= clip.start or clip.end > p['duration'] + .01 or clip.end - clip.start > 600:
        raise HTTPException(400, 'Choose a range within the video, up to 10 minutes long.')
    if clip.sticker_enabled and clip.sticker!='none' and clip.sticker_timing=='custom' and clip.sticker_at>=(clip.end-clip.start)/clip.speed:
        raise HTTPException(400,'Sticker start must be before the end of the output clip.')

@app.post('/api/projects/{project_id}/clips', status_code=201)
def create_clip(project_id: str, clip: ClipInput):
    def add(p):
        validate_clip(clip, p)
        p['clips'].append({**clip.model_dump(), 'id': uuid.uuid4().hex, 'score': None, 'reason': 'Manually selected', 'status': 'draft', 'file': None, 'error': None})
    p = store.mutate(project_id, add)
    if not p:
        raise HTTPException(404, 'Project not found')
    return p

@app.put('/api/projects/{project_id}/clips/{clip_id}')
def update_clip(project_id: str, clip_id: str, clip: ClipInput):
    def update(p):
        validate_clip(clip, p)
        c = next((c for c in p['clips'] if c['id'] == clip_id), None)
        if not c:
            raise HTTPException(404, 'Clip not found')
        if c['status'] in ('queued', 'rendering'):
            raise HTTPException(409, 'Wait for rendering to finish.')
        if c['start']!=clip.start or c['end']!=clip.end:
            selection.invalidate(c)
        c.update(**clip.model_dump(), status='draft', file=None, error=None)
    p = store.mutate(project_id, update)
    if not p:
        raise HTTPException(404, 'Project not found')
    return p

@app.post('/api/projects/{project_id}/clips/{clip_id}/render', status_code=202)
def export_clip(project_id: str, clip_id: str):
    def queue(p):
        if p['status'] in ('queued', 'transcribing', 'analyzing'):
            raise HTTPException(409, 'Wait for transcription to finish.')
        c = next((c for c in p['clips'] if c['id'] == clip_id), None)
        if not c:
            raise HTTPException(404, 'Clip not found')
        if c['status'] in ('queued', 'rendering'):
            raise HTTPException(409, 'This clip is already rendering.')
        c.update(status='queued', error=None)
    p = store.mutate(project_id, queue)
    if not p:
        raise HTTPException(404, 'Project not found')
    render_pool.submit(render_clip, project_id, clip_id)
    return p

@app.get('/api/projects/{project_id}/media/{kind}')
def get_media(project_id: str, kind: str):
    folder = directory(project_id)
    p = project_or_404(project_id)
    if kind == 'source':
        path, mime = folder / 'source', mimetypes.guess_type(p['name'])[0] or 'video/mp4'
    elif kind == 'poster':
        path, mime = folder / 'poster.jpg', 'image/jpeg'
    else:
        c = next((c for c in p['clips'] if c['id'] == kind and c['file'] and c['status'] == 'ready'), None)
        if not c:
            raise HTTPException(404, 'Render this clip first.')
        path, mime = folder / c['file'], 'video/webm' if c['file'].endswith('.webm') else 'video/mp4'
    if not path.is_file():
        raise HTTPException(404, 'Media file not found')
    # PyAV detects source formats; octet-stream remains playable with browser sniffing.
    suffix = path.suffix if kind not in ('source','poster') else ''
    return FileResponse(path, media_type=mime or 'video/mp4', filename=f'clipforge-{kind}{suffix}' if kind not in ('source', 'poster') else None, content_disposition_type='inline')


class LinkImportInput(GenerationInput, EffectSettings):
    source_kind: Literal['any','youtube'] = 'any'
    url: str = Field(min_length=8,max_length=4096)
    transcription_mode: Literal['fast','quick','balanced','accurate'] = 'fast'
    auto_generate: bool = True
    auto_render: bool = True


def run_link_import(job_id):
    folder=store.DATA/job_id
    registered=False
    try:
        job=store.import_get(job_id)
        options=LinkImportInput.model_validate(job['options'])
        store.import_update(job_id,status='importing',error=None,message='Reading video link…')
        folder.mkdir(exist_ok=True)
        def progress(percent,downloaded,message):
            store.import_update(job_id,progress=percent,downloaded_bytes=downloaded,message=message)
        result=importer.download_video(options.url,folder/'download',progress,max_height={'fast':480,'standard':720,'high':1080}[options.render_quality])
        source=folder/'source'
        result['path'].replace(source)
        info=media.probe(source)
        p={'id':job_id,'name':result['name'],'created_at':datetime.now(timezone.utc).isoformat(),'size':source.stat().st_size,**info,'status':'queued' if options.auto_generate else 'uploaded','error':None,'language':None,'transcript':[],'clips':[], 'source_url':options.url,'source_platform':result['platform'],'requested_clip_count':options.clip_count,'transcription_mode':options.transcription_mode,'speech_language':options.speech_language,'caption_script':options.caption_script,'transcription_progress':0,'selection_mode':options.selection_mode,'minimum_score':options.minimum_score,'default_effects':EffectSettings.model_validate(options.model_dump()).model_dump()}
        p['owner_id'] = job['owner_id']
        p.update(auto_count=options.auto_count,min_duration=options.min_duration,max_duration=options.max_duration)
        try:
            media.run(['-ss',str(min(1,info['duration']/2)),'-i',str(source),'-frames:v','1','-vf','scale=640:-2',str(folder/'poster.jpg')],timeout=30)
        except Exception:
            log.warning('Could not create imported video poster',exc_info=True)
        store.save(p)
        registered=True
        shutil.rmtree(folder/'download',ignore_errors=True)
        store.import_update(job_id,project_id=job_id,progress=100,status='processing' if options.auto_generate else 'ready',message='Video imported. Generating captions and clips…' if options.auto_generate else 'Video imported.')
        if options.auto_generate:
            process(job_id)
            p=store.get(job_id)
            if p['status']=='error':
                raise ValueError('Video imported, but automatic transcription failed: '+str(p['error']))
            if options.auto_render:
                ids=[]
                batch=p.get('clip_generation',{}).get('batch_id')
                def queue(project):
                    for c in project['clips']:
                        if c.get('batch_id')==batch and c['status']=='draft':
                            c.update(status='queued',error=None)
                            ids.append(c['id'])
                store.mutate(job_id,queue)
                for cid in ids:
                    render_pool.submit(render_clip,job_id,cid)
        store.import_update(job_id,status='ready',message='Import complete. Open the editor to preview clips and follow export progress.',error=None)
    except Exception as exc:
        log.exception('Link import failed')
        detail=(str(exc)+' Your downloaded video and any saved source transcript are kept. Open the imported video to recover processing.') if registered else importer.clean_error(exc)
        store.import_update(job_id,status='error',error=detail,message='Video imported; processing needs attention.' if registered else 'Could not complete link import.')
        if not registered and folder.resolve().parent==store.DATA.resolve():
            shutil.rmtree(folder,ignore_errors=True)


@app.post('/api/imports',status_code=202)
def import_link(options: LinkImportInput, request: Request):
    if options.source_kind=='youtube' and not importer.is_youtube_url(options.url):
        raise HTTPException(400,'Paste a YouTube video or Shorts link here. Use the general link importer for other websites.')
    try:
        importer.validate_public_url(options.url)
    except ValueError as exc:
        raise HTTPException(400,str(exc)) from exc
    job={'id':uuid.uuid4().hex,'status':'queued','progress':0,'downloaded_bytes':0,'project_id':None,'message':'Link import queued.','error':None,'created_at':datetime.now(timezone.utc).isoformat(),'options':options.model_dump()}
    job['owner_id'] = request.state.owner_id
    store.import_save(job)
    import_pool.submit(run_link_import,job['id'])
    return job


@app.get('/api/imports/{job_id}')
def import_status(job_id: str):
    job=store.import_get(job_id)
    if not job:
        raise HTTPException(404,'Link import not found')
    if job.get('project_id'):
        project=store.get(job['project_id'])
        if project and project.get('owner_id')==job.get('owner_id'):
            rendering=any(c['status'] in ('queued','rendering') for c in project['clips'])
            job['project_progress']={'stage':'rendering' if rendering else project['status'],
                                     'transcription_progress':project.get('transcription_progress',0),
                                     'total':len(project['clips']),'ready':sum(c['status']=='ready' for c in project['clips'])}
    return job
