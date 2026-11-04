"""Bounded YouTube thumbnails through the same origin; never an arbitrary URL proxy."""
import io
import re
import threading
import time
import urllib.request

from fastapi import HTTPException
from PIL import Image

from . import importer, store

slots = threading.BoundedSemaphore(4)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def fetch_image(video_id):
    if not re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id):
        raise HTTPException(422, 'Invalid YouTube video identifier.')
    folder = store.DATA / 'thumbnails'
    cached = folder / (video_id + '.jpg')
    if cached.is_file() and time.time() - cached.stat().st_mtime < 86400:
        return cached.read_bytes()
    if not slots.acquire(timeout=2):
        raise HTTPException(503, 'Thumbnail requests are busy. Retry later.')
    try:
        url = f'https://i.ytimg.com/vi/{video_id}/hqdefault.jpg'
        importer.validate_public_url(url)
        opener = urllib.request.build_opener(NoRedirect())
        with opener.open(urllib.request.Request(url, headers={'User-Agent':'ZyntraCut/1.0'}), timeout=10) as response:
            if response.headers.get_content_type() not in ('image/jpeg', 'image/png', 'image/webp'):
                raise ValueError('Not an image')
            data = response.read(2_000_001)
            if len(data) > 2_000_000:
                raise ValueError('Thumbnail too large')
        with Image.open(io.BytesIO(data)) as picture:
            if picture.width * picture.height > 16_000_000:
                raise ValueError('Thumbnail dimensions too large')
            picture.thumbnail((640, 480))
            output = io.BytesIO()
            picture.convert('RGB').save(output, format='JPEG', quality=85)
        data = output.getvalue()
        folder.mkdir(parents=True, exist_ok=True)
        # Only a complete image is ever served. Concurrent cache writes use unique names.
        import uuid
        temporary = folder / (video_id + '-' + uuid.uuid4().hex + '.tmp')
        try:
            temporary.write_bytes(data)
            temporary.replace(cached)
        finally:
            temporary.unlink(missing_ok=True)
        return data
    except Exception as exc:
        if cached.is_file():
            return cached.read_bytes()
        raise HTTPException(502, 'The source thumbnail is unavailable. You can still import this video.') from exc
    finally:
        slots.release()
