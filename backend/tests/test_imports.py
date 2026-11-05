import functools
import http.server
import socket
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend import importer,main,media,store

@pytest.mark.parametrize('url,expected',[
    ('https://youtu.be/w3tnaCFW_SE',True),('https://www.youtube.com/watch?v=w3tnaCFW_SE',True),
    ('https://m.youtube.com/shorts/example',True),('https://youtube.com.evil.example/watch?v=x',False),
    ('https://example.com/?url=https://youtube.com',False),('https://example.com/video.mp4',False),
    ('file:///youtube.com/video',False),('https://[broken',False),
])
def test_youtube_view_domain_validation(url,expected):
    assert importer.is_youtube_url(url)==expected

def test_youtube_mode_rejects_other_platform_before_download(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DATA',tmp_path)
    with TestClient(main.app) as client:
        client.get('/api/session')
        response=client.post('/api/imports',json={'url':'https://example.com/video.mp4','source_kind':'youtube'})
        assert response.status_code==400 and 'YouTube' in response.json()['detail']
        assert not store.all_imports()


@pytest.mark.parametrize('url',[
    'file:///C:/secret.mp4','ftp://example.com/video.mp4','http://localhost/video.mp4',
    'http://127.0.0.1/video.mp4','http://169.254.169.254/latest/meta-data/',
    'https://[::1]/video.mp4','https://10.0.0.1/a','https://user:pass@example.com/video',
    'http://example.com:8080/video.mp4','https://example.com/\nvideo',
])
def test_private_and_invalid_links_are_rejected(url):
    with pytest.raises(ValueError):
        importer.validate_public_url(url)


def test_dns_cannot_mix_public_and_private_addresses(monkeypatch):
    monkeypatch.setattr(socket,'getaddrinfo',lambda *a,**k:[(socket.AF_INET,socket.SOCK_STREAM,6,'',('93.184.216.34',443)),(socket.AF_INET,socket.SOCK_STREAM,6,'',('127.0.0.1',443))])
    with pytest.raises(ValueError,match='private'):
        importer.validate_public_url('https://example.com/video.mp4')


@pytest.fixture
def video_server(tmp_path,monkeypatch):
    path=tmp_path/'fixture.mp4'
    media.run(['-f','lavfi','-i','testsrc2=size=320x180:rate=15','-f','lavfi','-i','sine=frequency=440:sample_rate=16000','-t','2','-c:v','libx264','-c:a','aac',str(path)])
    class Handler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path=='/redirect':
                self.send_response(302);self.send_header('Location','http://127.0.0.1/private-video.mp4');self.end_headers()
            elif self.path=='/relative':
                self.send_response(302);self.send_header('Location','/fixture.mp4');self.end_headers()
            elif self.path=='/loop':
                self.send_response(302);self.send_header('Location','/loop');self.end_headers()
            else:
                super().do_GET()
        def do_POST(self):
            self.send_response(303);self.send_header('Location','/fixture.mp4');self.end_headers()
        def log_message(self,*args):
            pass
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(tmp_path)))
    base=f'http://127.0.0.1:{server.server_port}'
    original=importer.validate_public_url
    # Explicitly allow only this test fixture server. Production still rejects it.
    def fixture_only(url):
        if url.startswith(base+'/'):
            return url
        return original(url)
    monkeypatch.setattr(importer,'validate_public_url',fixture_only)
    worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
    yield base
    server.shutdown();server.server_close();worker.join(timeout=5)


def test_real_downloader_rejects_private_redirect(video_server,tmp_path):
    with pytest.raises(Exception,match='private'):
        importer.download_video(video_server+'/redirect',tmp_path/'redirect-result',lambda *args:None)


@pytest.mark.parametrize('url,enabled',[
    ('https://vt.tiktok.com/example/',True),('https://www.instagram.com/reel/example/',True),
    ('https://m.facebook.com/watch/?v=123',True),('https://fb.watch/example/',True),
    ('https://instagram.com.evil.example/video',False),('https://www.youtube.com/watch?v=123',False),
    ('https://example.com/video.mp4',False),
])
def test_browser_transport_is_scoped_to_social_domains(url,enabled):
    assert bool(importer.browser_options(url)) is enabled


def curl_downloader():
    from yt_dlp.networking.impersonate import ImpersonateTarget
    return importer.PublicYoutubeDL({'quiet':True,'logger':importer.DownloadLog(),'proxy':'','cachedir':False,
                                     'impersonate':ImpersonateTarget(client='chrome')})


def test_browser_transport_follows_validated_relative_redirect(video_server):
    with curl_downloader() as downloader:
        with downloader.urlopen(video_server+'/relative') as response:
            assert response.status==200
            assert response.read(12)[4:8]==b'ftyp'


def test_browser_transport_changes_post_to_get_for_303(video_server):
    from yt_dlp.networking import Request
    with curl_downloader() as downloader:
        with downloader.urlopen(Request(video_server+'/post',data=b'value=1')) as response:
            assert response.status==200
            assert response.read(12)[4:8]==b'ftyp'


def test_browser_transport_rejects_private_redirect(video_server):
    with curl_downloader() as downloader:
        with pytest.raises(Exception,match='private'):
            downloader.urlopen(video_server+'/redirect')


def test_browser_transport_bounds_redirect_loops(video_server):
    from yt_dlp.networking.exceptions import HTTPError
    with curl_downloader() as downloader:
        with pytest.raises(HTTPError) as error:
            downloader.urlopen(video_server+'/loop')
        assert error.value.redirect_loop


def test_browser_get_retries_the_failed_request_and_downloads_real_bytes(video_server,monkeypatch):
    from yt_dlp.networking.exceptions import RequestError
    original=importer.CurlCFFIRH._send
    attempts=[];progress=[]
    def unstable(self,request):
        attempts.append((id(self),request.url))
        if len(attempts)<3:raise RequestError('ConnectionResetError 10054: connection was reset')
        return original(self,request)
    monkeypatch.setattr(importer.CurlCFFIRH,'_send',unstable)
    monkeypatch.setattr(importer.time,'sleep',lambda seconds:None)
    with importer.PublicYoutubeDL({'quiet':True,'proxy':'','cachedir':False,**importer.browser_options('https://vt.tiktok.com/a'),
                                  '_clipforge_retry_progress':lambda *args:progress.append(args)}) as downloader:
        with downloader.urlopen(video_server+'/fixture.mp4') as response:
            assert response.read(12)[4:8]==b'ftyp'
    assert len(attempts)==3 and len({item[0] for item in attempts})==1
    assert progress==[(2,3),(3,3)]


@pytest.mark.parametrize('method',['GET','HEAD','POST'])
def test_request_reset_limit_and_no_post_replay(video_server,monkeypatch,method):
    from yt_dlp.networking import Request
    from yt_dlp.networking.exceptions import RequestError
    attempts=[]
    def fail(self,request):
        attempts.append(request.url);raise RequestError('ConnectionResetError 10054')
    monkeypatch.setattr(importer.CurlCFFIRH,'_send',fail)
    monkeypatch.setattr(importer.time,'sleep',lambda seconds:None)
    with curl_downloader() as downloader:
        with pytest.raises(RequestError):downloader.urlopen(Request(video_server+'/fixture.mp4',method=method))
    assert len(attempts)==(1 if method=='POST' else 3)


def test_browser_retry_rechecks_public_dns_before_next_request(video_server,monkeypatch):
    from yt_dlp.networking.exceptions import RequestError
    attempts=[];checks=[]
    def fail(self,request):
        attempts.append(request.url);raise RequestError('ConnectionResetError 10054')
    def validate(url):
        checks.append(url)
        if len(checks)>1:raise ValueError('Local and private-network links cannot be imported.')
        return url
    monkeypatch.setattr(importer.CurlCFFIRH,'_send',fail)
    monkeypatch.setattr(importer,'validate_public_url',validate)
    monkeypatch.setattr(importer.time,'sleep',lambda seconds:None)
    with curl_downloader() as downloader:
        with pytest.raises(RequestError,match='private'):downloader.urlopen(video_server+'/fixture.mp4')
    assert len(attempts)==1 and len(checks)==2


def test_request_http_denial_is_not_retried(video_server,monkeypatch):
    from yt_dlp.networking.exceptions import HTTPError
    original=importer.CurlCFFIRH._send;calls=[]
    def counted(self,request):calls.append(request.url);return original(self,request)
    monkeypatch.setattr(importer.CurlCFFIRH,'_send',counted)
    with curl_downloader() as downloader:
        with pytest.raises(HTTPError) as error:downloader.urlopen(video_server+'/missing.mp4')
    assert error.value.status==404 and len(calls)==1


def test_short_link_resolution_survives_later_reset(video_server,tmp_path,monkeypatch):
    original=importer.PublicYoutubeDL;validate=importer.validate_public_url;calls=[]
    short='https://vt.tiktok.com/test123/';canonical='https://www.tiktok.com/@fixture/video/123456789'
    monkeypatch.setattr(importer,'validate_public_url',lambda url:url if url in (short,canonical) else validate(url))
    class ResolvedThenReset(original):
        def extract_info(self,url,**kwargs):
            calls.append(url)
            if len(calls)==1:
                self.params['_clipforge_redirect'](short,canonical)
                raise importer.yt_dlp.utils.DownloadError('ConnectionResetError 10054')
            return super().extract_info(video_server+'/fixture.mp4',**kwargs)
    monkeypatch.setattr(importer,'PublicYoutubeDL',ResolvedThenReset)
    monkeypatch.setattr(importer.time,'sleep',lambda seconds:None)
    result=importer.download_video(short,tmp_path/'resolved',lambda *args:None)
    assert calls==[short,canonical] and media.probe(result['path'])['has_audio']


def test_connection_reset_has_actionable_network_message():
    message=importer.clean_error(ConnectionResetError(10054,'An existing connection was forcibly closed by the remote host'))
    assert 'Microsoft Edge' in message and 'mobile hotspot' in message
    assert 'does not by itself mean the video is private' in message


def test_reset_retries_then_downloads_real_video(video_server,tmp_path,monkeypatch):
    original=importer.PublicYoutubeDL
    calls=[];progress=[]
    class ResetOnce(original):
        def extract_info(self,*args,**kwargs):
            calls.append(args[0])
            if len(calls)==1:
                raise importer.yt_dlp.utils.DownloadError('ConnectionResetError(10054): connection was reset')
            return super().extract_info(*args,**kwargs)
    monkeypatch.setattr(importer,'PublicYoutubeDL',ResetOnce)
    monkeypatch.setattr(importer.time,'sleep',lambda seconds:None)
    result=importer.download_video(video_server+'/fixture.mp4',tmp_path/'retried',lambda *args:progress.append(args))
    assert len(calls)==2 and media.probe(result['path'])['has_audio']
    assert any('Retrying import (2/3)' in event[2] for event in progress)


@pytest.mark.parametrize('message,expected_calls',[
    ('ConnectionResetError(10054): connection was reset',3),('HTTP Error 403: Forbidden',1),
])
def test_retries_are_bounded_and_do_not_retry_access_denials(video_server,tmp_path,monkeypatch,message,expected_calls):
    calls=[]
    class Failure(importer.PublicYoutubeDL):
        def extract_info(self,*args,**kwargs):
            calls.append(args[0])
            raise importer.yt_dlp.utils.DownloadError(message)
    monkeypatch.setattr(importer,'PublicYoutubeDL',Failure)
    monkeypatch.setattr(importer.time,'sleep',lambda seconds:None)
    with pytest.raises(importer.yt_dlp.utils.DownloadError):
        importer.download_video(video_server+'/fixture.mp4',tmp_path/'failed',lambda *args:None)
    assert len(calls)==expected_calls


@pytest.mark.parametrize('quality,height',[('fast',480),('standard',720),('high',1080)])
def test_real_link_import_job_and_caption_defaults(video_server,tmp_path,monkeypatch,quality,height):
    data=tmp_path/'data';data.mkdir()
    monkeypatch.setattr(store,'DATA',data)
    requested=[]
    original=importer.download_video
    def observed(*args,**kwargs):
        requested.append(kwargs.get('max_height'))
        return original(*args,**kwargs)
    monkeypatch.setattr(importer,'download_video',observed)
    with TestClient(main.app) as client:
        assert client.get('/api/session').status_code == 200
        response=client.post('/api/imports',json={'url':video_server+'/fixture.mp4','auto_generate':False,'auto_render':False,'clip_count':30,'style':'neon','render_quality':quality})
        assert response.status_code==202,response.text
        job=response.json()
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            job=client.get('/api/imports/'+job['id']).json()
            if job['status'] in ('ready','error'):
                break
            time.sleep(.1)
        assert job['status']=='ready',job
        p=client.get('/api/projects/'+job['project_id']).json()
        assert p['duration']==pytest.approx(2,abs=.2)
        assert p['requested_clip_count']==30
        assert p['default_effects']['style']=='neon'
        assert p['default_effects']['render_quality']==quality
        assert requested==[height]
        assert p['source_url']==video_server+'/fixture.mp4'
        other=TestClient(main.app)
        other.get('/api/session')
        assert other.get('/api/imports/'+job['id']).status_code==404
        assert other.get('/api/projects/'+p['id']).status_code==404
        assert other.get(f"/api/projects/{p['id']}/media/source").status_code==404
        other.close()
        assert (data/p['id']/'source').is_file()
        assert client.get(f"/api/projects/{p['id']}/media/source").status_code==200
        assert client.delete('/api/projects/'+p['id']).status_code==204


def test_import_failure_reports_error_without_fake_project(video_server,tmp_path,monkeypatch):
    data=tmp_path/'data';data.mkdir()
    monkeypatch.setattr(store,'DATA',data)
    with TestClient(main.app) as client:
        assert client.get('/api/session').status_code == 200
        assert client.post('/api/imports',json={'url':'file:///secret.mp4'}).status_code==400
        assert client.post('/api/imports',json={'url':video_server+'/fixture.mp4','clip_count':101}).status_code==422
        job=client.post('/api/imports',json={'url':video_server+'/missing.mp4','auto_generate':False}).json()
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            job=client.get('/api/imports/'+job['id']).json()
            if job['status']=='error':
                break
            time.sleep(.1)
        assert job['status']=='error',job
        assert job['error']
        assert job['project_id'] is None
        assert not store.all_projects()
        assert not (data/job['id']).exists()
        assert client.get('/api/imports/unknown').status_code==404
