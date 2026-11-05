"""Real English speech -> independent local subtitle outputs -> playable MP4s.
Uses the cached public JFK sample from backend.scripts.verify_whisper. No user projects.
"""
import json
import shutil
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from faster_whisper import WhisperModel
from backend import main,media,store,translation


def main_verify():
    root=Path('artifacts').resolve();cache=store.DATA
    model=WhisperModel('small',device='cpu',compute_type='int8',download_root=str(cache/'models'),local_files_only=True)
    main.models['small']=model
    reports=[]
    with tempfile.TemporaryDirectory(prefix='zyntra-translate-') as temp:
        store.DATA=Path(temp)
        source=store.DATA/'source.mp4'
        media.run(['-f','lavfi','-i','color=c=0x121925:s=640x360:r=24','-i',str(cache/'jfk.flac'),'-shortest','-c:v','libx264','-c:a','aac',str(source)])
        with TestClient(main.app) as client:
            client.get('/api/session')
            for script in ['urdu','hindi','roman_urdu','english']:
                with source.open('rb') as file:
                    response=client.post('/api/projects',files={'file':('English speech.mp4',file,'video/mp4')})
                assert response.status_code==201,response.text
                pid=response.json()['id'];base=f'/api/projects/{pid}'
                # Run the actual job synchronously in this isolated verification.
                store.mutate(pid,lambda p:p.update(caption_script=script,speech_language='auto',transcription_mode='accurate',selection_mode='all',requested_clip_count=1))
                main.process(pid);p=store.get(pid)
                assert p['status']=='ready',p.get('error')
                assert p['language']=='en' and p['transcript'],p
                clip=p['clips'][0]
                assert client.put(base+'/clips/'+clip['id'],json={**clip,'render_quality':'fast'}).status_code==200
                main.render_clip(pid,clip['id']);p=store.get(pid);clip=p['clips'][0]
                assert clip['status']=='ready',clip.get('error')
                output=store.DATA/pid/clip['file'];assert media.probe(output)['has_audio']
                target=root/f'translation-english-{script}.mp4';shutil.copyfile(output,target)
                media.run(['-ss','3','-i',str(target),'-frames:v','1',str(root/f'translation-english-{script}.png')])
                srt=client.get(base+'/subtitles').text;(root/f'translation-english-{script}.srt').write_text(srt,encoding='utf-8')
                translated=script!='english'
                assert all(bool(s.get('words'))!=translated for s in p['transcript'])
                reports.append({'script':script,'detected_speech':p['language'],'source':' '.join(s['text'] for s in p['source_transcript']),
                                'subtitles':' '.join(s['text'] for s in p['transcript']),'timing':'sentence translation' if translated else 'source words','export':media.probe(target)})
                assert client.delete(base).status_code==204
                print(f'English speech -> {script}: actual ASR, translation, MP4 and SRT passed',flush=True)
    # Exercise the reverse model directions too; output text is retained for review.
    reverse=[]
    for source,text in [('ur','آپ کیسے ہیں؟'),('hi','आप कैसे हैं?')]:
        reverse.append({'source_language':source,'input':text,'english':translation.translate_texts([text],source,'en')[0]})
    (root/'translation-verification.json').write_text(json.dumps({'status':'passed','results':reports,'reverse':reverse},ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':main_verify()
