import io
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend import main,store,thumbnails


def test_thumbnail_proxy_only_accepts_valid_ids_caches_images_and_handles_upstream_failure(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DATA',tmp_path)
    data=io.BytesIO();Image.new('RGB',(480,360),'blue').save(data,format='JPEG')
    calls=[]
    class Remote(io.BytesIO):
        headers=SimpleNamespace(get_content_type=lambda:'image/jpeg')
    def download(request,timeout):
        calls.append(request.full_url)
        if len(calls)>1:raise OSError('Network offline')
        return Remote(data.getvalue())
    monkeypatch.setattr(thumbnails.importer,'validate_public_url',lambda url:url)
    monkeypatch.setattr(thumbnails.urllib.request,'build_opener',lambda *args:SimpleNamespace(open=download))
    with TestClient(main.app) as client:
        assert client.get('/api/discover/abcdefghijk/thumbnail').status_code==401
        client.get('/api/session')
        response=client.get('/api/discover/abcdefghijk/thumbnail')
        assert response.status_code==200 and response.headers['content-type']=='image/jpeg'
        assert Image.open(io.BytesIO(response.content)).size==(480,360)
        assert calls==['https://i.ytimg.com/vi/abcdefghijk/hqdefault.jpg']
        assert client.get('/api/discover/abcdefghijk/thumbnail').status_code==200 and len(calls)==1
        assert client.get('/api/discover/lmnopqrstuv/thumbnail').status_code==502
        assert client.get('/api/discover/not-a-url/thumbnail').status_code==422
        assert not list((tmp_path/'thumbnails').glob('*.tmp'))
