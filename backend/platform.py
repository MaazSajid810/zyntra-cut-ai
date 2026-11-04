"""Independent local workspace features. No competitor service integration."""
import json
import re
import shutil
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from typing import Literal

from fastapi import HTTPException,Request,UploadFile,Form
from fastapi.responses import FileResponse
from PIL import Image,ImageDraw,ImageFont,ImageOps
from pydantic import BaseModel,Field

from . import assets,importer,media,store

CATEGORIES={'All':'long form highlights','Podcasts':'podcast full episode','Interviews':'interview full conversation','Business':'business interview','Comedy':'comedy podcast','True crime':'true crime documentary','News':'news interview','Education':'educational explainer','Sports':'sports highlights','Gaming':'gaming highlights','Fitness':'fitness training','Tech':'technology review'}
discovery_lock=threading.Lock()
studio_pool=ThreadPoolExecutor(max_workers=1)


def settings_get(key,default=None):
    with store.connect() as db:
        row=db.execute('SELECT value FROM settings WHERE key=?',(key,)).fetchone()
        return json.loads(row[0]) if row else default


def settings_put(key,value):
    with store.connect() as db:
        db.execute('INSERT INTO settings VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,json.dumps(value)))


def claim_studio(job):
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        jobs=[json.loads(r[0]) for r in db.execute("SELECT value FROM settings WHERE key LIKE 'studio:%'")]
        active=[j for j in jobs if j['status'] in ('queued','rendering')]
        if any(j.get('owner_id')==job['owner_id'] for j in active):raise HTTPException(409,'Wait for your current Studio render to finish.')
        if len(active)>=4:raise HTTPException(429,'Studio is busy. Retry after an active render finishes.')
        if sum(j.get('owner_id')==job['owner_id'] for j in jobs)>=100:raise HTTPException(409,'Delete older Studio results before creating more.')
        db.execute('INSERT INTO settings VALUES (?,?)',('studio:'+job['id'],json.dumps(job)))


def recover_studio():
    with store.connect() as db:
        for key,value in list(db.execute("SELECT key,value FROM settings WHERE key LIKE 'studio:%'")):
            job=json.loads(value)
            if job['status'] in ('queued','rendering'):
                job.update(status='error',error='Studio rendering was interrupted. Reuse the settings to create a new result.')
                db.execute('UPDATE settings SET value=? WHERE key=?',(json.dumps(job),key))


def public_search(query):
    import yt_dlp
    with yt_dlp.YoutubeDL({'quiet':True,'no_warnings':True,'extract_flat':True,'skip_download':True,'socket_timeout':12,'retries':1,'extractor_retries':0,'playlistend':12}) as downloader:
        data=downloader.extract_info('ytsearch12:'+query,download=False)
    items=[]
    for v in data.get('entries',[]):
        ident=v.get('id','')
        if not re.fullmatch(r'[A-Za-z0-9_-]{11}',ident):continue
        thumbs=v.get('thumbnails') or []
        thumb=next((t['url'] for t in reversed(thumbs) if t.get('url','').startswith('https://i.ytimg.com/')),None)
        views=v.get('view_count')
        items.append({'id':ident,'title':v.get('title') or 'Untitled video','channel':v.get('channel') or v.get('uploader') or '',
                      'url':'https://www.youtube.com/watch?v='+ident,'thumbnail':thumb or f'https://i.ytimg.com/vi/{ident}/hqdefault.jpg',
                      'duration':v.get('duration'),'views':views if isinstance(views,int) and views>=0 else None,'views_per_hour':None})
    return items


def discover(category,refresh=False):
    if category not in CATEGORIES:raise HTTPException(422,'Choose a listed discovery category.')
    key='discovery:'+category
    with discovery_lock:
        previous=settings_get(key)
        now=time.time()
        if previous and now-previous['observed_at']<(30 if refresh else 3600):return previous
        try:items=public_search(CATEGORIES[category])
        except Exception:
            if previous:return {**previous,'stale':True,'message':'YouTube could not be refreshed. These are the last successful results.'}
            raise HTTPException(502,'Public discovery is unavailable from YouTube right now. Retry later or paste your own supported video link.')
        old={x['id']:x for x in (previous or {}).get('items',[])}
        elapsed=now-previous['observed_at'] if previous else 0
        for item in items:
            before=old.get(item['id'],{}).get('views')
            if elapsed>=300 and before is not None and item['views'] is not None and item['views']>=before:
                item['views_per_hour']=round((item['views']-before)*3600/elapsed,1)
        result={'items':items,'observed_at':now,'stale':False,'category':category,'source':'YouTube public relevance search',
                'message':'Discovery results are relevance-based, not a verified trending chart. View velocity appears only after two observations at least five minutes apart.'}
        settings_put(key,result)
        return result


class WizardInput(BaseModel):
    message:str=Field(min_length=1,max_length=2000)
    project_id:str|None=Field(default=None,pattern=r'^[a-f0-9]{32}$')
    clip_id:str|None=Field(default=None,pattern=r'^[a-f0-9]{32}$')


class SourcePreviewInput(BaseModel):
    url:str=Field(min_length=1,max_length=4096)


def parse_command(text,project_id=None,clip_id=None):
    raw=text.strip();s=raw.lower()
    url=re.search(r'https?://[^\s<>]+',raw)
    if url:
        count=re.search(r'(?:generate|create|make|banao|bana)\s+(\d+)\s+clips?',s)
        bounds=re.search(r'(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*(?:s\b|seconds?|sec\b)',s)
        n=int(count[1]) if count else 5
        a,b=(float(bounds[1]),float(bounds[2])) if bounds else (8,60)
        if not 1<=n<=100 or not 3<=a<=b<=180:raise ValueError('Use 1-100 clips and a 3-180 second duration range.')
        return {'operation':'import','body':{'url':url.group(0).rstrip('.,'),'clip_count':n,'min_duration':a,'max_duration':b,'auto_generate':True,'auto_render':True},'description':f'Import this video, generate up to {n} qualified clips of {a:g}-{b:g} seconds and prepare previews.'}
    count=re.search(r'(?:generate|create|make|banao|bana)\s+(\d+)\s+clips?',s)
    if count:
        if not project_id:raise ValueError('Choose an uploaded project first, or paste a public video link.')
        n=int(count[1]);bounds=re.search(r'(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*(?:s\b|seconds?|sec\b)',s)
        a,b=(float(bounds[1]),float(bounds[2])) if bounds else (8,60)
        if not 1<=n<=100 or not 3<=a<=b<=180:raise ValueError('Use 1-100 clips and a 3-180 second duration range.')
        return {'operation':'generate','body':{'clip_count':n,'min_duration':a,'max_duration':b,'auto_render':True},'description':f'Generate up to {n} qualified clips, {a:g}-{b:g} source seconds each.'}
    if not project_id or not clip_id:raise ValueError('Choose a project and a clip for editing. Try “generate 5 clips, 15-30 seconds” to create clips.')
    changes={}
    trim=re.fullmatch(r'trim\s+(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*(?:seconds?|s)?',s)
    if trim:
        a,b=float(trim[1]),float(trim[2])
        if b<=a:raise ValueError('Trim end must be after trim start. Times refer to the source video.')
        changes={'start':a,'end':b}
    elif s in ('vertical','square','landscape','portrait','original'):
        changes={'aspect':s}
    elif (m:=re.fullmatch(r'(?:caption|captions)\s+(?:style\s+)?(mint|clean|yellow|boxed|neon|minimal|cyan|orange|red|comic|elegant|shadow|none)',s)):
        changes={'style':m[1]}
    elif (m:=re.fullmatch(r'(?:font|caption)\s+size\s+(\d+)',s)):
        size=int(m[1])
        if not 18<=size<=96:raise ValueError('Caption size must be 18-96.')
        changes={'subtitle_size':size}
    elif (m:=re.fullmatch(r'speed\s+(\d+(?:\.\d+)?)x?',s)):
        speed=float(m[1])
        if not 1<=speed<=4:raise ValueError('Use a speed from 1x to 4x.')
        changes={'speed':speed}
    elif (m:=re.fullmatch(r'voice\s+(none|deep|high|radio|echo|mute)',s)):
        changes={'voice_effect':m[1]}
    elif s in ('render','export','prepare export'):
        return {'operation':'render','body':{},'description':'Render the selected saved clip. Download remains manual.'}
    else:raise ValueError('Local commands: generate 5 clips, 15-30 seconds; captions yellow; font size 72; trim 2-15; vertical; speed 1.2x; voice deep; render. This is a command parser, not a general chat model.')
    return {'operation':'edit','body':changes,'description':'Apply '+', '.join(f'{k.replace("_"," ")}: {v}' for k,v in changes.items())+' and render an updated preview.'}


class StudioOptions(BaseModel):
    text:str=Field(min_length=1,max_length=600)
    kind:Literal['video','image']='video'
    style:Literal['bold','minimal','cinematic']='bold'
    duration:int=Field(default=8,ge=3,le=15)
    quality:Literal['480','720','1080']='480'


class ChatMessage(BaseModel):
    role:Literal['user','assistant']
    text:str=Field(min_length=1,max_length=3000)


class ChatHistory(BaseModel):
    messages:list[ChatMessage]=Field(max_length=80)


def owned_job(studio_id,owner):
    job=settings_get('studio:'+studio_id)
    if not job or job.get('owner_id')!=owner:raise HTTPException(404,'Studio result not found')
    return job


def studio_render(studio_id):
    key='studio:'+studio_id
    job=settings_get(key)
    folder=store.DATA/studio_id
    try:
        job.update(status='rendering',error=None);settings_put(key,job)
        opts=StudioOptions.model_validate(job['options'])
        width=int(opts.quality);height=round(width*16/9)//2*2
        colors={'bold':('#171a32','#ffffff','#383cff'),'minimal':('#f5f5f3','#181b1d','#c8f65b'),'cinematic':('#11151a','#f2e4cf','#766144')}
        bg,fg,accent=colors[opts.style]
        image=Image.new('RGB',(width,height),bg)
        if job.get('photo'):
            with assets.load_static_image(folder/'photo.png','image') as photo:
                image=ImageOps.fit(photo.convert('RGB'),(width,height))
            overlay=Image.new('RGBA',image.size,(0,0,0,110));image=Image.alpha_composite(image.convert('RGBA'),overlay).convert('RGB')
        draw=ImageDraw.Draw(image)
        font=ImageFont.truetype(str(media.FONTS/'Poppins-Bold.ttf'),max(20,width//13))
        lines=[]
        for paragraph in opts.text.splitlines() or ['']:
            line=''
            for word in paragraph.split():
                candidate=(line+' '+word).strip()
                if draw.textlength(candidate,font=font)>width*.82 and line:lines.append(line);line=word
                else:line=candidate
            if line:lines.append(line)
        if len(lines)>14:raise ValueError('This text is too long for one design. Use a shorter title or split it into multiple designs.')
        line_height=int(font.size*1.5);y=(height-len(lines)*line_height)//2
        draw.rounded_rectangle((width*.08,max(12,y-35),width*.92,min(height-12,y+len(lines)*line_height+35)),radius=width//25,fill=bg)
        for line in lines:
            # Shrink exceptionally long unbroken words to stay within the safe area.
            line_font=font
            while draw.textlength(line,font=line_font)>width*.82 and line_font.size>12:line_font=ImageFont.truetype(str(media.FONTS/'Poppins-Bold.ttf'),line_font.size-1)
            if draw.textlength(line,font=line_font)>width*.82:raise ValueError('An unbroken word is too long for this design. Add spaces or use shorter text.')
            draw.text((width/2,y),line,font=line_font,fill=fg,anchor='mt');y+=line_height
        draw.rounded_rectangle((width*.38,height*.83,width*.62,height*.838),radius=3,fill=accent)
        image.save(folder/'design.png')
        if opts.kind=='video':
            frames=opts.duration*24
            vf=f"zoompan=z='min(zoom+0.0005,1.06)':d={frames}:s={width}x{height}:fps=24,fade=t=in:d=0.25,fade=t=out:st={opts.duration-.35}:d=0.35,format=yuv420p"
            media.run(['-i',str(folder/'design.png'),'-vf',vf,'-t',str(opts.duration),'-an','-c:v','libx264','-preset','veryfast','-threads','1','-movflags','+faststart',str(folder/'source')+'.mp4'],timeout=300)
            (folder/'source.mp4').replace(folder/'source')
            info=media.probe(folder/'source')
            Image.open(folder/'design.png').resize((360,640)).save(folder/'poster.jpg')
            store.save({'id':studio_id,'owner_id':job['owner_id'],'name':opts.text[:80],'created_at':job['created_at'],'size':(folder/'source').stat().st_size,**info,'status':'uploaded','error':None,'language':None,'transcript':[],'clips':[],'studio_origin':'local-design'})
            job['project_id']=studio_id
        job.update(status='ready',error=None);settings_put(key,job)
    except Exception as exc:
        job.update(status='error',error=str(exc));settings_put(key,job)


def register_routes(app):
    @app.post('/api/source-preview')
    def source_preview(options:SourcePreviewInput):
        try:return importer.preview_source(options.url)
        except ValueError as exc:raise HTTPException(400,str(exc)) from exc
        except Exception as exc:raise HTTPException(502,'Could not read the video preview. '+importer.clean_error(exc)) from exc

    @app.get('/api/discover')
    def discovery(category:str='All',refresh:bool=False):return discover(category,refresh)

    @app.post('/api/wizard/plan')
    def wizard_plan(options:WizardInput,request:Request):
        if options.project_id:
            p=store.get(options.project_id)
            if not p or p.get('owner_id')!=request.state.owner_id:raise HTTPException(404,'Project not found')
            if options.clip_id and not any(c['id']==options.clip_id for c in p['clips']):raise HTTPException(404,'Clip not found')
        try:plan=parse_command(options.message,options.project_id,options.clip_id)
        except ValueError as exc:raise HTTPException(400,str(exc)) from exc
        return plan

    @app.get('/api/wizard/history')
    def wizard_history(request:Request):return settings_get('wizard:'+request.state.owner_id,{'messages':[]})

    @app.put('/api/wizard/history')
    def wizard_save(options:ChatHistory,request:Request):
        value=options.model_dump();settings_put('wizard:'+request.state.owner_id,value);return value

    @app.delete('/api/wizard/history',status_code=204)
    def wizard_clear(request:Request):
        with store.connect() as db:db.execute('DELETE FROM settings WHERE key=?',('wizard:'+request.state.owner_id,))

    @app.get('/api/studio')
    def studio_list(request:Request):
        with store.connect() as db:
            rows=db.execute("SELECT value FROM settings WHERE key LIKE 'studio:%' ORDER BY rowid DESC").fetchall()
        result=[]
        for row in rows:
            job=json.loads(row[0])
            if job.get('owner_id')!=request.state.owner_id:continue
            if job['status']=='ready' and not (store.DATA/job['id']/('source' if job['options']['kind']=='video' else 'design.png')).is_file():
                job.update(status='deleted',error='The media was deleted with its source project.')
            result.append({k:v for k,v in job.items() if k!='owner_id'})
        return result

    @app.post('/api/studio',status_code=202)
    def studio_create(request:Request,text:str=Form(...),kind:Literal['video','image']=Form('video'),style:Literal['bold','minimal','cinematic']=Form('bold'),duration:int=Form(8),quality:Literal['480','720','1080']=Form('480'),file:UploadFile|None=None):
        try:opts=StudioOptions(text=text.strip(),kind=kind,style=style,duration=duration,quality=quality)
        except ValueError:raise HTTPException(422,'Use a 1-600 character title, 3-15 seconds and a supported style/quality.')
        studio_id=uuid.uuid4().hex;folder=store.DATA/studio_id;folder.mkdir()
        try:
            if file:
                raw=file.file.read(20*1024**2+1)
                if len(raw)>20*1024**2:raise HTTPException(413,'Photo exceeds the 20 MB limit.')
                temp=folder/'photo.upload';temp.write_bytes(raw)
                try:
                    with assets.load_static_image(temp,'image') as photo:photo.save(folder/'photo.png')
                except ValueError as exc:raise HTTPException(400,str(exc)) from exc
                temp.unlink()
            job={'id':studio_id,'owner_id':request.state.owner_id,'created_at':datetime.now(timezone.utc).isoformat(),'status':'queued','error':None,'options':opts.model_dump(),'photo':bool(file),'project_id':None}
            claim_studio(job);studio_pool.submit(studio_render,studio_id)
            return {k:v for k,v in job.items() if k!='owner_id'}
        except Exception:
            shutil.rmtree(folder,ignore_errors=True);raise

    @app.get('/api/studio/{studio_id}/media')
    def studio_media(studio_id:str,request:Request):
        job=owned_job(studio_id,request.state.owner_id)
        if job['status']!='ready':raise HTTPException(409,'This result is not ready.')
        name='source' if job['options']['kind']=='video' else 'design.png'
        path=store.DATA/studio_id/name
        if not path.is_file():raise HTTPException(404,'This result was deleted with its project.')
        return FileResponse(path,media_type='video/mp4' if name=='source' else 'image/png',filename='zyntracut-studio.'+('mp4' if name=='source' else 'png'),content_disposition_type='inline')

    @app.delete('/api/studio/{studio_id}',status_code=204)
    def studio_delete(studio_id:str,request:Request):
        job=owned_job(studio_id,request.state.owner_id)
        if job['status'] in ('queued','rendering'):raise HTTPException(409,'Wait for rendering to finish.')
        if job.get('project_id'):
            from .main import delete_project
            p=store.get(job['project_id'])
            if p and p.get('owner_id')==request.state.owner_id:delete_project(job['project_id'])
        else:
            folder=(store.DATA/studio_id).resolve()
            if folder.parent!=store.DATA.resolve():raise HTTPException(400,'Invalid Studio path.')
            try:shutil.rmtree(folder)
            except FileNotFoundError:pass
            except PermissionError:raise HTTPException(409,'Close this preview in other players and retry.')
        with store.connect() as db:db.execute('DELETE FROM settings WHERE key=?',('studio:'+studio_id,))
