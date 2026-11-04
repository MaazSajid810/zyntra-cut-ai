"""Fetch redistributable OFL fonts and their licenses from Google Fonts."""
from concurrent.futures import ThreadPoolExecutor
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request

root=Path(__file__).resolve().parents[1]/'public'/'fonts'
root.mkdir(parents=True,exist_ok=True)
families={
    'anton':['Anton-Regular.ttf'],
    'bebasneue':['BebasNeue-Regular.ttf'],
    'poppins':['Poppins-Regular.ttf','Poppins-Bold.ttf'],
    'righteous':['Righteous-Regular.ttf'],
    'bangers':['Bangers-Regular.ttf'],
    'lobster':['Lobster-Regular.ttf'],
    'pacifico':['Pacifico-Regular.ttf'],
    'kalam':['Kalam-Bold.ttf'],
    'notosansdevanagari':['NotoSansDevanagari[wdth,wght].ttf'],
    'notosansarabic':['NotoSansArabic[wdth,wght].ttf'],
    'notosansgurmukhi':['NotoSansGurmukhi[wdth,wght].ttf'],
    'notosansbengali':['NotoSansBengali[wdth,wght].ttf'],
}
def fetch(item):
    family,filename=item
    url=f'https://raw.githubusercontent.com/google/fonts/main/ofl/{family}/{filename}'
    path=root/(family+'-OFL.txt' if filename=='OFL.txt' else filename.split('[')[0]+'.ttf' if '[' in filename else filename)
    with urllib.request.urlopen(url,timeout=45) as response:data=response.read()
    if filename.endswith('.ttf') and data[:4] not in (b'\0\1\0\0',b'OTTO'):
        raise ValueError(f'Invalid font download: {filename}')
    path.write_bytes(data)
    return {'file':path.name,'source':url,'sha256':hashlib.sha256(data).hexdigest()}
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--families',nargs='+',choices=sorted(families),help='Refresh only selected font families; existing manifest entries are retained.')
    selected=parser.parse_args().families or list(families)
    items=[(family,filename) for family in selected for filename in [*families[family],'OFL.txt']]
    with ThreadPoolExecutor(max_workers=4) as pool:report=list(pool.map(fetch,items))
    manifest=root/'manifest.json'
    previous=json.loads(manifest.read_text(encoding='utf-8')) if manifest.exists() else []
    replacements={entry['file']:entry for entry in report}
    report=[entry for entry in previous if entry['file'] not in replacements]+report
    manifest.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(f'Downloaded {sum(len(families[family]) for family in selected)} fonts and {len(selected)} OFL licenses.')
