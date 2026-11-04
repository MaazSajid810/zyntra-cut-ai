"""Public video downloads using yt-dlp. No browser cookies or credentials."""
import ipaddress
import logging
import math
import re
import shutil
import socket
import stat
import time
from pathlib import Path
from urllib.parse import urljoin,urlsplit

import yt_dlp
from yt_dlp.networking._requests import RequestsRH
from yt_dlp.networking._curlcffi import CurlCFFIRH
from yt_dlp.networking._helper import get_redirect_method
from yt_dlp.networking.impersonate import ImpersonateTarget
from yt_dlp.networking.exceptions import HTTPError,RequestError

from . import media

log=logging.getLogger('clipforge.imports')
MAX_BYTES=2*1024**3

def is_youtube_url(url):
    try:
        parts=urlsplit(url)
        host=(parts.hostname or '').rstrip('.').lower()
        return parts.scheme in ('http','https') and (host in ('youtube.com','youtu.be','www.youtu.be') or host.endswith('.youtube.com'))
    except ValueError:
        return False

def validate_public_url(url):
    if not isinstance(url,str) or len(url)>4096 or any(ord(c)<32 for c in url):
        raise ValueError('Paste a valid public video link.')
    try:
        parts=urlsplit(url)
        port=parts.port
    except ValueError as exc:
        raise ValueError('This video link is not valid.') from exc
    if parts.scheme not in ('http','https') or not parts.hostname or parts.username or parts.password:
        raise ValueError('Use a public HTTP or HTTPS video link without embedded login credentials.')
    if port not in (None,80,443):
        raise ValueError('Only standard HTTP/HTTPS video links are supported.')
    host=parts.hostname.rstrip('.').lower()
    if host=='localhost' or host.endswith(('.localhost','.local','.internal')):
        raise ValueError('Local and private-network links cannot be imported.')
    try:
        addresses={item[4][0] for item in socket.getaddrinfo(host,port or (443 if parts.scheme=='https' else 80),type=socket.SOCK_STREAM)}
    except OSError as exc:
        raise ValueError('Could not resolve this video website. Check the link and your internet connection.') from exc
    if not addresses or any(not ipaddress.ip_address(address.split('%')[0]).is_global for address in addresses):
        raise ValueError('Local and private-network links cannot be imported.')
    return url


class PublicRequestsRH(RequestsRH):
    def _create_instance(self,*args,**kwargs):
        session=super()._create_instance(*args,**kwargs)
        send=session.send
        def public_send(request,**send_options):
            # Session.send is also used for every redirect and CDN request.
            try:
                validate_public_url(request.url)
            except ValueError as exc:
                raise RequestError(str(exc)) from exc
            return send(request,**send_options)
        session.send=public_send
        return session


class PublicYoutubeDL(yt_dlp.YoutubeDL):
    def build_request_director(self,handlers,preferences=None):
        director=super().build_request_director([PublicRequestsRH,PublicCurlCFFIRH],preferences)
        for handler in director.handlers.values():
            if isinstance(handler,PublicCurlCFFIRH):
                handler.retry_progress=self.params.get('_clipforge_retry_progress')
                handler.remember_redirect=self.params.get('_clipforge_redirect')
        return director


class PublicCurlCFFIRH(CurlCFFIRH):
    """Browser-compatible HTTPS with every redirect checked before it is sent."""
    def _send_with_reset_recovery(self,request):
        # Retry the failing public GET/HEAD, preserving the session/cookies and
        # successful extraction work. Restarting the entire extractor alone can
        # repeatedly lose its session before reaching a flaky CDN request.
        attempts=3 if request.method in ('GET','HEAD') else 1
        for attempt in range(attempts):
            try:
                return super()._send(request)
            except HTTPError:
                # Access denials, rate limits and redirects have their own rules.
                raise
            except RequestError as exc:
                if attempt==attempts-1 or not is_connection_reset(exc):
                    raise
                # Recheck DNS on every retry as well as every redirect.
                try:
                    validate_public_url(request.url)
                except ValueError as unsafe:
                    raise RequestError(str(unsafe)) from unsafe
                callback=getattr(self,'retry_progress',None)
                if callback:callback(attempt+2,attempts)
                time.sleep(.4*(attempt+1))

    def _create_instance(self,*args,**kwargs):
        session=super()._create_instance(*args,**kwargs)
        request=session.request
        def public_request(*args,**options):
            # libcurl's internal redirect handling would skip URL validation.
            options['allow_redirects']=False
            return request(*args,**options)
        session.request=public_request
        return session

    def _send(self,request):
        request=request.copy()
        for hop in range(6):
            try:
                validate_public_url(request.url)
            except ValueError as exc:
                raise RequestError(str(exc)) from exc
            try:
                return self._send_with_reset_recovery(request)
            except HTTPError as exc:
                response=exc.response
                location=response.headers.get('Location')
                if response.status not in (301,302,303,307,308) or not location:
                    raise
                if hop==5:
                    raise HTTPError(response,redirect_loop=True) from exc
                target=urljoin(request.url,location)
                try:
                    validate_public_url(target)
                except ValueError as unsafe:
                    response.close()
                    raise RequestError(str(unsafe)) from unsafe
                callback=getattr(self,'remember_redirect',None)
                if callback:callback(request.url,target)
                method=get_redirect_method(request.method,response.status)
                previous=urlsplit(request.url)
                following=urlsplit(target)
                if (previous.scheme,previous.netloc)!=(following.scheme,following.netloc):
                    for header in ('Authorization','Cookie','Proxy-Authorization'):
                        request.headers.pop(header,None)
                if method!=request.method:
                    request.data=None
                    for header in ('Content-Type','Content-Length'):
                        request.headers.pop(header,None)
                request.method=method
                request.url=target
                response.close()


def browser_options(url):
    """Use browser TLS only for the social sites that need it."""
    host=(urlsplit(url).hostname or '').lower().rstrip('.')
    social=('tiktok.com','instagram.com','facebook.com','fb.watch')
    if any(host==domain or host.endswith('.'+domain) for domain in social):
        return {'impersonate':ImpersonateTarget(client='chrome')}
    return {}


def is_tiktok_short_url(url):
    parts=urlsplit(url)
    host=(parts.hostname or '').lower().rstrip('.')
    return host in ('vt.tiktok.com','vm.tiktok.com') or (host in ('tiktok.com','www.tiktok.com') and parts.path.startswith('/t/'))


class DownloadLog:
    def debug(self,message):
        pass
    def warning(self,message):
        log.info('%s',message)
    def error(self,message):
        log.warning('%s',message)


def is_connection_reset(error):
    return any(marker in str(error).lower() for marker in ('10054','connection was reset','connectionreseterror','forcibly closed','connection aborted'))


def clean_error(error):
    text=re.sub(r'\x1b\[[0-9;]*m','',str(error))
    text=re.sub(r'^ERROR:\s*','',text).strip()
    text=text[:1000] or 'The video could not be downloaded.'
    if '.part-frag' in text.lower() and any(marker in text.lower() for marker in ('winerror 2','errno 2','no such file','cannot find the file')):
        return ('A temporary download fragment was missing while the video was being assembled. '
                'Retry importing the same link. This is a local download-file error, not evidence that the video is private.')
    if is_connection_reset(text):
        return ('The connection to this video website was reset before import could finish. '
                'Check whether the same link opens in Microsoft Edge on this internet connection. '
                'If Edge also fails, try another network (for example a mobile hotspot); '
                'if Edge opens it but importing fails, the site may be blocking automated downloads. '
                'Then retry the public video link, or upload the video file. '
                'A connection reset does not by itself mean the video is private.')
    return text+' Public video links only; private/login-only, DRM, deleted, region-restricted or bot-blocked videos may not be available. You can upload the video file instead.'


def preview_source(url):
    """Read real source metadata without downloading media or creating a project.

    Extraction still contacts the public website, so it uses the same redirect
    and DNS validation as importing. A successful preview cannot guarantee that
    a later media download will be permitted by the source platform.
    """
    url=validate_public_url(url.strip())
    options={
        'noplaylist':True,'playlist_items':'1','quiet':True,'no_warnings':False,
        'logger':DownloadLog(),'skip_download':True,'cachedir':False,
        'socket_timeout':15,'retries':1,'extractor_retries':1,
        'proxy':'','remote_components':set(),
        'js_runtimes':{'node':{'path':shutil.which('node')}},
        **browser_options(url),
    }
    with PublicYoutubeDL(options) as downloader:
        info=downloader.extract_info(url,download=False)
    if not isinstance(info,dict) or info.get('_type') in ('playlist','multi_video','url','url_transparent'):
        raise ValueError('Paste a single video or reel link, not a playlist, profile, or carousel.')
    if info.get('is_live') or info.get('live_status') in ('is_live','is_upcoming'):
        raise ValueError('Live streams and upcoming broadcasts cannot be imported.')
    if info.get('availability') in ('private','premium_only','subscriber_only','needs_auth'):
        raise ValueError('This video requires access or login. Preview and import support public videos only.')
    formats=info.get('formats') or []
    if info.get('has_drm') or (formats and all(f.get('has_drm') for f in formats)):
        raise ValueError('DRM-protected videos cannot be imported.')
    duration=info.get('duration')
    duration=duration if isinstance(duration,(int,float)) and not isinstance(duration,bool) and math.isfinite(duration) and duration>0 else None
    if duration and duration>14400:
        raise ValueError('Video imports are limited to four hours.')
    if (info.get('filesize') or info.get('filesize_approx') or 0)>MAX_BYTES:
        raise ValueError('This video exceeds the 2 GB import limit.')

    def text(value,limit):
        return ''.join(c for c in value if ord(c)>=32).strip()[:limit] if isinstance(value,str) else ''

    canonical=info.get('webpage_url') or url
    try:canonical=validate_public_url(canonical)
    except (ValueError,TypeError):canonical=url
    thumbnail=None
    candidates=[info.get('thumbnail')]+[item.get('url') for item in reversed(info.get('thumbnails') or []) if isinstance(item,dict)]
    for candidate in candidates:
        if not isinstance(candidate,str):continue
        try:thumbnail=validate_public_url(candidate);break
        except ValueError:continue
    return {'url':canonical,'original_url':url,'title':text(info.get('title'),240) or 'Untitled video',
            'duration':duration,'platform':text(info.get('extractor_key') or info.get('extractor'),80) or 'Web',
            'thumbnail':thumbnail,'channel':text(info.get('channel') or info.get('uploader'),160) or None}


def download_folder_bytes(folder):
    """Fragment files may disappear between directory listing and stat.

    yt-dlp renames/appends/removes fragments concurrently with progress hooks.
    Inspect each entry once and tolerate only a vanished file; other disk errors
    must remain visible and the total-size limit must still be enforced.
    """
    total=0
    for path in folder.iterdir():
        try:
            info=path.stat()
        except FileNotFoundError:
            continue
        if stat.S_ISREG(info.st_mode):
            total+=info.st_size
    return total


def download_video(url,folder,progress,max_height=720):
    if max_height not in (480,720,1080):
        raise ValueError('Choose 480p, 720p or 1080p video quality.')
    validate_public_url(url)
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    last_update=0
    last_downloaded=0
    resolved_url=url
    def remember_redirect(previous,target):
        nonlocal resolved_url
        host=(urlsplit(target).hostname or '').lower().rstrip('.')
        if is_tiktok_short_url(previous) and (host=='tiktok.com' or host.endswith('.tiktok.com')) and '/video/' in urlsplit(target).path:
            # Keep a successfully resolved short link if a later request drops.
            # Otherwise every whole-import retry starts from the fragile HEAD
            # short-link request and loses this already discovered public URL.
            resolved_url=target
    def retry_progress(attempt,total):
        progress(None,last_downloaded,f'Connection interrupted. Reconnecting to video website ({attempt}/{total})...')
    def on_progress(data):
        nonlocal last_update,last_downloaded
        downloaded=data.get('downloaded_bytes',0)
        last_downloaded=downloaded
        total=data.get('total_bytes') or data.get('total_bytes_estimate')
        stored=download_folder_bytes(folder)
        if downloaded>MAX_BYTES or stored>MAX_BYTES:
            raise ValueError('This video exceeds the 2 GB import limit.')
        if time.monotonic()-last_update>=.75 or data.get('status')=='finished':
            progress(min(99,round(downloaded/total*100)) if total else None,downloaded,'Downloading video…')
            last_update=time.monotonic()
    def check(info,*,incomplete=False):
        if info.get('is_live') or info.get('live_status') in ('is_live','is_upcoming'):
            return 'Live streams and upcoming broadcasts cannot be imported.'
        if info.get('duration') and info['duration']>14400:
            return 'Video imports are limited to four hours.'
        if (info.get('filesize') or info.get('filesize_approx') or 0)>MAX_BYTES:
            return 'This video exceeds the 2 GB import limit.'
        return None
    options={
        'format':f'bestvideo[height<={max_height}]+bestaudio/best[height<={max_height}]/best',
        'outtmpl':str(folder/'source.%(ext)s'), 'merge_output_format':'mp4',
        'noplaylist':True, 'playlist_items':'1', 'quiet':True, 'no_warnings':False,
        'logger':DownloadLog(), 'progress_hooks':[on_progress], 'match_filter':check,
        'ffmpeg_location':media.FFMPEG, 'js_runtimes':{'node':{'path':shutil.which('node')}},
        'socket_timeout':20, 'retries':2, 'fragment_retries':2,
        'max_filesize':MAX_BYTES, 'overwrites':True, 'continuedl':False,
        'hls_prefer_native':True, 'concurrent_fragment_downloads':2,
        'proxy':'', 'cachedir':str(folder/'.cache'),
        'remote_components':set(),
        '_clipforge_retry_progress':retry_progress,'_clipforge_redirect':remember_redirect,
        **browser_options(url),
    }
    progress(0,0,'Reading public video link…')
    for attempt in range(3):
        try:
            with PublicYoutubeDL(options) as downloader:
                info=downloader.extract_info(resolved_url,download=False)
                if not info or info.get('_type') in ('playlist','multi_video','url','url_transparent'):
                    raise ValueError('Paste a single video or reel link, not a playlist, profile, or carousel.')
                reason=check(info)
                if reason:
                    raise ValueError(reason)
                for stream in info.get('requested_formats') or [info]:
                    if stream.get('protocol') not in ('http','https','m3u8_native','http_dash_segments'):
                        raise ValueError('This video uses a streaming protocol that cannot be imported here. Upload the file instead.')
                    if stream.get('url'):
                        validate_public_url(stream['url'])
                result=downloader.process_ie_result(info,download=True)
                candidates=[p for p in folder.glob('source.*') if p.is_file() and p.suffix.lower() in ('.mp4','.webm','.mkv','.mov','.flv','.avi','.m4v','.ts')]
                if not candidates:
                    raise ValueError('The platform did not provide a downloadable video. Try a public single-video link or upload the file.')
                output=max(candidates,key=lambda p:p.stat().st_size)
                if output.stat().st_size>MAX_BYTES:
                    raise ValueError('This video exceeds the 2 GB import limit.')
                media.probe(output)
                return {'path':output,'name':str((result or info).get('title') or 'Imported video')[:180]+output.suffix,'platform':info.get('extractor_key') or info.get('extractor') or 'Web'}
        except Exception as exc:
            if attempt==2 or not is_connection_reset(exc):
                raise
            progress(None,0,f'Connection interrupted. Retrying import ({attempt+2}/3)...')
            time.sleep(1)
