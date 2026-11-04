"""Verify a real public link; --download additionally downloads and probes it."""
import argparse
import json
import tempfile
from pathlib import Path

from backend import importer,media

parser=argparse.ArgumentParser()
parser.add_argument('url')
parser.add_argument('--download',action='store_true')
args=parser.parse_args()
try:
    if args.download:
        with tempfile.TemporaryDirectory(prefix='clipforge-link-test-') as tmp:
            result=importer.download_video(args.url,Path(tmp),lambda percent,size,message:print(json.dumps({'progress':percent,'bytes':size,'message':message}),flush=True))
            print(json.dumps({'status':'passed','name':result['name'],'platform':result['platform'],**media.probe(result['path'])},indent=2))
    else:
        importer.validate_public_url(args.url)
        with importer.PublicYoutubeDL({'quiet':True,'logger':importer.DownloadLog(),'noplaylist':True,'skip_download':True,'socket_timeout':20,'retries':1,'proxy':'','js_runtimes':{'node':{}},'cachedir':False,**importer.browser_options(args.url)}) as downloader:
            info=downloader.extract_info(args.url,download=False)
            print(json.dumps({'status':'passed','title':info.get('title'),'duration':info.get('duration'),'platform':info.get('extractor_key'),'formats':len(info.get('formats',[]))},indent=2))
except Exception as exc:
    print(json.dumps({'status':'failed','error':importer.clean_error(exc)},indent=2))
    raise SystemExit(1)
