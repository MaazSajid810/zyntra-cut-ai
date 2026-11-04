"""Preview contract and security checks; upstream metadata is explicitly stubbed."""
import ipaddress
import socket

import pytest
from fastapi.testclient import TestClient

from backend import importer,main,store


@pytest.fixture
def preview_env(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DATA',tmp_path)
    def resolve(host,port,**kwargs):
        try:address=str(ipaddress.ip_address(host))
        except ValueError:address='93.184.216.34'
        return [(socket.AF_INET,socket.SOCK_STREAM,6,'',(address,port))]
    monkeypatch.setattr(importer.socket,'getaddrinfo',resolve)
    state={'calls':[],'options':[],'info':{'title':'Actual upstream title','duration':2091.5,
          'extractor_key':'Youtube','webpage_url':'https://www.youtube.com/watch?v=abcdefghijk',
          'thumbnail':'https://i.ytimg.com/vi/abcdefghijk/hqdefault.jpg','channel':'Source channel',
          'url':'https://cdn.example.com/private-signed-stream?token=not-returned'}}
    class MetadataOnly:
        def __init__(self,options):state['options'].append(options)
        def __enter__(self):return self
        def __exit__(self,*args):return False
        def extract_info(self,url,download):
            state['calls'].append((url,download))
            if state.get('error'):raise state['error']
            return state['info']
        def process_ie_result(self,*args,**kwargs):pytest.fail('Preview attempted a media download')
        def download(self,*args,**kwargs):pytest.fail('Preview attempted a media download')
    monkeypatch.setattr(importer,'PublicYoutubeDL',MetadataOnly)
    with TestClient(main.app) as client:
        yield client,state


def test_source_preview_requires_private_guest_session(preview_env):
    client,state=preview_env
    assert client.post('/api/source-preview',json={'url':'https://youtu.be/abcdefghijk'}).status_code==401
    assert not state['calls']


def test_preview_returns_real_metadata_without_media_or_jobs(preview_env):
    client,state=preview_env;client.get('/api/session')
    result=client.post('/api/source-preview',json={'url':' https://youtu.be/abcdefghijk '})
    assert result.status_code==200,result.text
    assert result.json()=={'url':'https://www.youtube.com/watch?v=abcdefghijk',
                          'original_url':'https://youtu.be/abcdefghijk','title':'Actual upstream title',
                          'duration':2091.5,'platform':'Youtube','channel':'Source channel',
                          'thumbnail':'https://i.ytimg.com/vi/abcdefghijk/hqdefault.jpg'}
    assert state['calls']==[('https://youtu.be/abcdefghijk',False)]
    assert state['options'][0]['skip_download'] is True
    assert state['options'][0]['cachedir'] is False
    assert state['options'][0]['proxy']==''
    assert not store.all_projects() and not store.all_imports()
    assert all(p.name.startswith('clipforge.db') for p in store.DATA.iterdir())
    assert 'not-returned' not in result.text


@pytest.mark.parametrize('url',[
    'file:///C:/secret.mp4','https://user:pass@example.com/video','http://localhost/video',
    'http://127.0.0.1/video','http://169.254.169.254/latest/meta-data','https://10.0.0.1/video',
    'https://example.com:8080/video','https://example.com/\nvideo',
])
def test_preview_rejects_unsafe_url_before_extractor(preview_env,url):
    client,state=preview_env;client.get('/api/session')
    assert client.post('/api/source-preview',json={'url':url}).status_code==400
    assert not state['calls'] and not state['options']


def test_preview_omits_unsafe_thumbnail_and_canonical_link(preview_env):
    client,state=preview_env;client.get('/api/session')
    state['info'].update(webpage_url='http://127.0.0.1/private',thumbnail='http://10.0.0.1/image.jpg')
    result=client.post('/api/source-preview',json={'url':'https://example.com/video'}).json()
    assert result['url']=='https://example.com/video' and result['thumbnail'] is None


@pytest.mark.parametrize('info,reason',[
    ({'_type':'playlist','entries':[]},'single video'),
    ({'is_live':True},'Live streams'),
    ({'live_status':'is_upcoming'},'upcoming'),
    ({'availability':'private'},'public videos'),
    ({'availability':'needs_auth'},'login'),
    ({'has_drm':True},'DRM'),
    ({'formats':[{'has_drm':True}]},'DRM'),
    ({'duration':14401},'four hours'),
    ({'filesize':importer.MAX_BYTES+1},'2 GB'),
])
def test_preview_rejects_unimportable_metadata(preview_env,info,reason):
    client,state=preview_env;client.get('/api/session');state['info']=info
    result=client.post('/api/source-preview',json={'url':'https://example.com/video'})
    assert result.status_code==400 and reason in result.json()['detail']
    assert not store.all_projects() and not store.all_imports()


def test_blocked_platform_returns_honest_upstream_error(preview_env):
    client,state=preview_env;client.get('/api/session')
    state['error']=importer.yt_dlp.utils.DownloadError('This video is private. Sign in to confirm access.')
    result=client.post('/api/source-preview',json={'url':'https://example.com/video'})
    assert result.status_code==502
    assert 'private' in result.json()['detail'] and 'upload the video file' in result.json()['detail']


def test_missing_metadata_is_unknown_not_fabricated(preview_env):
    client,state=preview_env;client.get('/api/session');state['info']={'duration':float('inf')}
    result=client.post('/api/source-preview',json={'url':'https://example.com/video'}).json()
    assert result['title']=='Untitled video' and result['duration'] is None
    assert result['channel'] is None and result['thumbnail'] is None


def test_preview_post_is_protected_against_cross_site_requests(preview_env):
    client,state=preview_env;client.get('/api/session')
    result=client.post('/api/source-preview',json={'url':'https://example.com/video'},headers={'Origin':'https://untrusted.example'})
    assert result.status_code==403 and not state['calls']
