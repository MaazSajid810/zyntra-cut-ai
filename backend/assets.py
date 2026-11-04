"""Owned project media assets; no remote URLs or arbitrary filesystem paths."""
import mimetypes
import uuid
from pathlib import Path
from typing import Literal

import av
from fastapi import HTTPException,UploadFile
from fastapi.responses import FileResponse
from PIL import Image,ImageOps,UnidentifiedImageError

from . import media,store

REFERENCES={'logo_asset_id':'logo','filler_asset_id':'filler','music_asset_id':'music','image_asset_id':'image'}
LIMITS={'logo':10*1024**2,'filler':100*1024**2,'music':30*1024**2,'image':20*1024**2}
LABELS={'logo':'Channel logo','filler':'B-roll video','music':'Background music','image':'Photo'}
Image.MAX_IMAGE_PIXELS=16_777_216


def load_static_image(path,kind):
    try:
        with Image.open(path) as image:
            if image.format not in ('PNG','JPEG','WEBP') or getattr(image,'is_animated',False):
                raise ValueError(f'Use a static PNG, JPEG or WebP {"logo" if kind=="logo" else "photo"}.')
            if max(image.size)>4096:raise ValueError('Image dimensions must be at most 4096 pixels.')
            return ImageOps.exif_transpose(image).convert('RGBA')
    except OSError as exc:
        raise ValueError('This image could not be decoded. Choose an intact PNG, JPEG or WebP file.') from exc


def validate_references(project,settings):
    for field,kind in REFERENCES.items():
        value=settings.get(field)
        if value and not any(a['id']==value and a['kind']==kind for a in project.get('assets',[])):
            raise HTTPException(400,f'Select a {kind} uploaded to this project.')


def register_routes(app):
    @app.get('/api/assets/limits')
    def asset_limits():
        return {kind:{'max_bytes':limit,'label':LABELS[kind]} for kind,limit in LIMITS.items()}

    @app.get('/api/projects/{project_id}/assets')
    def list_assets(project_id:str):
        return store.get(project_id).get('assets',[])

    @app.post('/api/projects/{project_id}/assets',status_code=201)
    def upload_asset(project_id:str,file:UploadFile,kind:Literal['logo','filler','music','image']):
        project=store.get(project_id)
        if len(project.get('assets',[]))>=25:raise HTTPException(400,'A project can hold up to 25 uploaded assets.')
        folder=store.DATA/project_id
        asset_id=uuid.uuid4().hex
        temporary=folder/f'asset-{asset_id}.upload'
        final=None
        try:
            size=0
            with temporary.open('wb') as target:
                while chunk:=file.file.read(1024**2):
                    size+=len(chunk)
                    if size>LIMITS[kind]:raise HTTPException(413,f'{LABELS[kind]} exceeds the {LIMITS[kind]//1024**2} MB limit. Choose a smaller file.')
                    target.write(chunk)
            if not size:raise ValueError('Choose a non-empty media file.')
            info={}
            if kind in ('logo','image'):
                with load_static_image(temporary,kind) as logo:
                    final=folder/f'asset-{asset_id}.png'
                    logo.save(final)
                    if final.stat().st_size>LIMITS[kind]:
                        raise ValueError(f'{LABELS[kind]} is too large after image normalization. Resize the image and retry.')
                    info={'width':logo.width,'height':logo.height}
            else:
                if kind=='filler':
                    info=media.probe(temporary)
                    if info['duration']>600:raise ValueError('B-roll must be at most 10 minutes long.')
                else:
                    with av.open(str(temporary)) as container:
                        if not container.streams.audio:raise ValueError('Choose a file containing audio.')
                        duration=float(container.duration/av.time_base) if container.duration else 0
                        if not 0<duration<=1200:raise ValueError('Music must have a known duration of at most 20 minutes.')
                        info={'duration':duration,'has_audio':True}
                extension=Path(file.filename or '').suffix.lower()
                if extension not in ('.mp4','.mov','.mkv','.webm','.mp3','.wav','.ogg','.flac','.m4a','.aac'):extension='.bin'
                final=folder/f'asset-{asset_id}{extension}'
                temporary.replace(final)
            asset={'id':asset_id,'kind':kind,'name':(file.filename or kind)[:160],'file':final.name,'size':final.stat().st_size,**info}
            def save(p):
                if len(p.get('assets',[]))>=25:raise HTTPException(400,'A project can hold up to 25 assets.')
                p.setdefault('assets',[]).append(asset)
            store.mutate(project_id,save)
            return asset
        except HTTPException:raise
        except (ValueError,UnidentifiedImageError,Image.DecompressionBombError,av.error.FFmpegError) as exc:
            raise HTTPException(400,str(exc) or 'This media could not be decoded.') from exc
        finally:
            temporary.unlink(missing_ok=True)
            # Remove partial outputs only when they were not registered.
            if final and final.exists() and not any(a['id']==asset_id for a in (store.get(project_id) or {}).get('assets',[])):
                final.unlink(missing_ok=True)

    @app.get('/api/projects/{project_id}/assets/{asset_id}')
    def get_asset(project_id:str,asset_id:str):
        asset=next((a for a in store.get(project_id).get('assets',[]) if a['id']==asset_id),None)
        if not asset:raise HTTPException(404,'Asset not found')
        return FileResponse(store.DATA/project_id/asset['file'],media_type=mimetypes.guess_type(asset['file'])[0] or 'application/octet-stream')

    @app.delete('/api/projects/{project_id}/assets/{asset_id}',status_code=204)
    def delete_asset(project_id:str,asset_id:str):
        def remove(p):
            if p['status'] in ('queued','transcribing','analyzing') or any(c['status'] in ('queued','rendering') for c in p['clips']):
                raise HTTPException(409,'Wait for processing to finish before deleting an asset.')
            asset=next((a for a in p.get('assets',[]) if a['id']==asset_id),None)
            if not asset:raise HTTPException(404,'Asset not found')
            if any(c.get(key)==asset_id for c in [*p['clips'],p.get('default_effects',{})] for key in REFERENCES):
                raise HTTPException(409,'Remove this asset from clip settings before deleting it.')
            (store.DATA/project_id/asset['file']).unlink(missing_ok=True)
            p['assets']=[a for a in p['assets'] if a['id']!=asset_id]
        store.mutate(project_id,remove)
