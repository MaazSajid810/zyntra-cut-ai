"""Live app import/media/export verification in a separate temporary guest.

Only this script's created projects are deleted; existing user projects stay intact.
Run against the running local app after updating its backend.
"""
import json
import time
from pathlib import Path
import requests


def verify():
    root='http://127.0.0.1:3000';session=requests.Session();session.trust_env=False
    session.get(root+'/api/session',timeout=15).raise_for_status()
    results=[]
    for platform,url in [('TikTok','https://vt.tiktok.com/ZSgmnSyeU/'),('Instagram','https://www.instagram.com/reel/DegREppNbu4/')]:
        pid=None;job_id=None;started=time.monotonic()
        try:
            response=session.post(root+'/api/imports',json={'url':url,'auto_generate':False,'auto_render':False,'render_quality':'standard'},timeout=20)
            response.raise_for_status();job=response.json();job_id=job['id']
            while time.monotonic()-started<180:
                response=session.get(root+'/api/imports/'+job_id,timeout=15);response.raise_for_status();job=response.json()
                if job['status'] in ('ready','error'):break
                time.sleep(.4)
            pid=job.get('project_id')
            item={'platform':platform,'url':url,'status':job['status'],'seconds':round(time.monotonic()-started,2),'error':job.get('error')}
            results.append(item)
            if job['status']=='ready' and pid:
                response=session.get(root+'/api/projects/'+pid,timeout=15);response.raise_for_status();p=response.json()
                preview=session.get(root+f'/api/projects/{pid}/media/source',headers={'Range':'bytes=0-1023'},timeout=20)
                poster=session.get(root+f'/api/projects/{pid}/media/poster',timeout=15)
                item.update(duration=p['duration'],width=p['width'],height=p['height'],audio=p['has_audio'],source_preview_status=preview.status_code,source_bytes=len(preview.content),poster_status=poster.status_code)
                assert preview.status_code==206 and len(preview.content)==1024 and poster.status_code==200
                # An actual source-range render proves imported media can reach
                # preview/export. This is a manual test clip, not simulated AI.
                response=session.post(root+f'/api/projects/{pid}/clips',json={'title':'Recovery verification','start':0,'end':min(4,p['duration']),'style':'none','render_quality':'fast'},timeout=15)
                response.raise_for_status();clip=response.json()['clips'][0]
                session.post(root+f'/api/projects/{pid}/clips/{clip["id"]}/render',timeout=15).raise_for_status()
                deadline=time.monotonic()+90
                while time.monotonic()<deadline:
                    p=session.get(root+'/api/projects/'+pid,timeout=15).json();clip=p['clips'][0]
                    if clip['status'] in ('ready','error'):break
                    time.sleep(.3)
                assert clip['status']=='ready',clip
                exported=session.get(root+f'/api/projects/{pid}/media/{clip["id"]}',timeout=20);exported.raise_for_status()
                Path(f'artifacts/recovery-{platform.lower()}-preview.mp4').write_bytes(exported.content)
                item.update(clip_status=clip['status'],clip_bytes=len(exported.content),clip_inline='inline' in exported.headers.get('Content-Disposition',''))
            print(json.dumps(item),flush=True)
        finally:
            if not pid and job_id:
                pid=session.get(root+'/api/imports/'+job_id,timeout=15).json().get('project_id')
            if pid:
                deleted=session.delete(root+'/api/projects/'+pid,timeout=15)
                print('Verification project cleanup:',deleted.status_code,flush=True)
    Path('artifacts/social-recovery-live-api.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    assert all(item['status']=='ready' and item.get('clip_status')=='ready' for item in results),results


if __name__=='__main__':verify()
