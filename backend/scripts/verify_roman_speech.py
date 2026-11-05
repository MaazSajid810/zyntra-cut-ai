"""Real FLEURS Urdu/Hindi audio -> cached Whisper -> Roman/Hindi captions -> MP4.

Run with --fetch once (network), then without it for local processing. Add --hindi for Devanagari exports using the cached small model.
FLEURS: google/fleurs, CC BY 4.0, https://huggingface.co/datasets/google/fleurs.
Isolated temporary project database; never edits user projects.
"""
import argparse
import json
import os
import shutil
import tempfile
import time
import urllib.request
from datetime import datetime,timezone
from pathlib import Path

ARTIFACTS=Path('artifacts').resolve()
ARTIFACTS.mkdir(exist_ok=True)
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--fetch',action='store_true')
parser.add_argument('--hindi',action='store_true')
parser.add_argument('--mode',choices=('fast','balanced','accurate'))
parser.add_argument('--model',choices=('base','small'))
parser.add_argument('--auto-language',action='store_true')
args=parser.parse_args()
target='hindi' if args.hindi else 'roman_urdu'
mode=args.mode or 'accurate'
model_name=args.model or 'small'
if target=='hindi':os.environ['WHISPER_HINDI_MODEL']=model_name
else:os.environ['WHISPER_ROMAN_MODEL']=model_name
prefix='hindi' if target=='hindi' else 'roman'
if args.mode or args.model:prefix+=f'-{mode}-{model_name}'
if args.auto_language:prefix+='-auto'

if args.fetch:
    for language,config in [('ur','ur_pk'),('hi','hi_in')]:
        split='test' if language=='ur' else 'validation'
        url=f'https://datasets-server.huggingface.co/first-rows?dataset=google/fleurs&config={config}&split={split}'
        with urllib.request.urlopen(url,timeout=30) as response:
            row=json.load(response)['rows'][0]['row']
        with urllib.request.urlopen(row['audio'][0]['src'],timeout=45) as response:
            (ARTIFACTS/f'roman-{language}-source.wav').write_bytes(response.read())
        (ARTIFACTS/f'roman-{language}-source.json').write_text(json.dumps({'dataset':'google/fleurs','config':config,'split':split,'id':row['id'],'reference':row['raw_transcription'],'license':'CC BY 4.0'},ensure_ascii=False,indent=2),encoding='utf-8')
        print(f'Cached public {language} speech fixture',flush=True)
    raise SystemExit(0)

from fastapi.testclient import TestClient
from faster_whisper import WhisperModel
from backend import main,store,media,romanization,captions

cache=store.DATA/'models'
recognizer=WhisperModel(model_name,device='cpu',compute_type='int8',download_root=str(cache),local_files_only=True)
main.models[model_name]=recognizer
if target!='hindi' and mode!='fast':main.model=recognizer
results=[]
def fail_case(message,project,language):
    report={'status':'failed','checked_at':datetime.now(timezone.utc).isoformat(),
            'caption_script':target,'transcription_mode':mode,'model':model_name,
            'automatic_language':args.auto_language,'failed_language':language,'error':message,
            'detected_language':project.get('language'),'raw_segments':project.get('source_transcript',[]),
            'transcript':project.get('transcript',[]),'clip_generation':project.get('clip_generation'),
            'results':results}
    (ARTIFACTS/f'{prefix}-real-speech.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    raise AssertionError(message)

for language in ['ur','hi']:
    with tempfile.TemporaryDirectory(prefix='zyntracut-roman-') as tmp:
        store.DATA=Path(tmp)
        source=store.DATA/'speech.mp4'
        media.run(['-f','lavfi','-i','color=c=0x141925:s=640x360:r=24','-i',str(ARTIFACTS/f'roman-{language}-source.wav'),'-shortest','-c:v','libx264','-c:a','aac',str(source)])
        with TestClient(main.app) as client:
            client.get('/api/session')
            with source.open('rb') as f:
                response=client.post('/api/projects',files={'file':('roman-speech.mp4',f,'video/mp4')})
            assert response.status_code==201,response.text
            pid=response.json()['id'];base=f'/api/projects/{pid}'
            started=time.monotonic()
            assert client.post(base+'/transcribe',json={'transcription_mode':mode,'speech_language':'auto' if args.auto_language else language,'caption_script':target,'clip_count':1,'selection_mode':'all','auto_render':True,'generated_settings':{'render_quality':'fast','aspect':'original'}}).status_code==202
            deadline=time.monotonic()+(480 if target=='hindi' else 240)
            while time.monotonic()<deadline:
                p=client.get(base).json()
                assert p['status']!='error',p
                if p['status']=='ready' and p.get('clip_generation') and not p['clips']:
                    fail_case('Known speech fixture produced no candidate clip; inspect recorded ASR text and language.',p,language)
                if p['status']=='ready' and p['clips'] and all(c['status'] in ('ready','error') for c in p['clips']):break
                time.sleep(.2)
            assert p['status']=='ready' and p['transcript'],p
            assert all(c['status']=='ready' for c in p['clips']),p
            native=' '.join(s['text'] for s in p['source_transcript'])
            latin=' '.join(s['text'] for s in p['transcript'])
            # Whisper can emit Latin Hindustani directly, especially tiny. That
            # is valid Roman output, not proof of native-script recognition.
            expected=('hi',) if target=='hindi' else ('ur','hi') if args.auto_language else (language,)
            assert p['language'] in expected,(p['language'],native)
            assert native.strip(),native
            if target=='hindi':assert romanization.HINDI.search(native) and not romanization.URDU.search(native),native
            assert not romanization.URDU.search(latin),latin
            assert bool(romanization.HINDI.search(latin))==(target=='hindi'),latin
            # Whisper can omit zero-duration words. Require genuine timestamps,
            # and let the renderer use its existing phrase fallback if unaligned.
            assert any(s.get('words') for s in p['source_transcript']),p['source_transcript']
            assert any(s.get('words') for s in p['transcript']),p['transcript']
            clip=p['clips'][0];output=store.DATA/pid/clip['file']
            info=media.probe(output)
            assert info['has_audio'] and info['duration']>1
            ass=next((store.DATA/pid).glob('*.ass')).read_text(encoding='utf-8')
            assert r'\1c' in ass and not romanization.URDU.search(ass)
            assert bool(romanization.HINDI.search(ass))==(target=='hindi')
            if target=='hindi':assert 'Noto Sans Devanagari' in ass
            srt=client.get(base+'/subtitles').text
            assert not romanization.URDU.search(srt)
            assert bool(romanization.HINDI.search(srt))==(target=='hindi')
            shutil.copyfile(output,ARTIFACTS/f'{prefix}-{language}-preview.mp4')
            (ARTIFACTS/f'{prefix}-{language}.srt').write_text(srt,encoding='utf-8')
            media.run(['-ss',str(min(2,info['duration']/2)),'-i',str(output),'-frames:v','1','-y',str(ARTIFACTS/f'{prefix}-{language}-frame.png')])
            tail=p['transcript'][-1]
            tail_time=max(.1,min(info['duration']-.1,(tail['start']+tail['end'])/2-clip['start']))
            media.run(['-ss',str(tail_time),'-i',str(output),'-frames:v','1','-y',str(ARTIFACTS/f'{prefix}-{language}-tail-frame.png')])
            aligned=sum(captions.aligned(s) for s in p['transcript'])
            results.append({'speech_language':language,'detected_language':p['language'],'native_asr':native,'subtitle_text':latin,'elapsed_seconds':round(time.monotonic()-started,2),'aligned_segments':aligned,'phrase_fallback_segments':len(p['transcript'])-aligned,'segment_count':len(p['transcript']),'export':info,'reference':json.loads((ARTIFACTS/f'roman-{language}-source.json').read_text(encoding='utf-8'))})
            assert client.delete(base).status_code==204
            print(f'{language}: real speech and automatic {target} captioned MP4 passed',flush=True)
(ARTIFACTS/f'{prefix}-real-speech.json').write_text(json.dumps({'status':'passed','checked_at':datetime.now(timezone.utc).isoformat(),'caption_script':target,'transcription_mode':mode,'model':model_name,'automatic_language':args.auto_language,'results':results},ensure_ascii=False,indent=2),encoding='utf-8')
