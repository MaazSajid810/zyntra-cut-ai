"""Install the pinned MIT-licensed M2M100 CPU INT8 translation model (~494 MB)."""
import hashlib
from pathlib import Path
import shutil
import tempfile
import urllib.request
from backend.translation import ROOT

REPO='JustFrederik/m2m_100_418m_ct2_int8'
REVISION='1aeed44db4dd61a486bba44acf54c76507082a2c'
HASHES={
    'model.bin':'6c8ef4e814a02d5947ab80710f93f3d4e776bf4b668ab3bb7996ff050b69d111',
    'spm.128k.model':'d8f7c76ed2a5e0822be39f0a4f95a55eb19c78f4593ce609e2edbc2aea4d380a',
}


def main():
    ROOT.mkdir(parents=True,exist_ok=True)
    destination=ROOT/'m2m100'
    required=('config.json','model.bin','shared_vocabulary.txt','spm.128k.model','README.md')
    if all((destination/name).is_file() for name in required):
        print('M2M100 is already installed.',flush=True);return
    with tempfile.TemporaryDirectory(dir=ROOT,prefix='m2m-install-') as temporary:
        folder=Path(temporary)
        for name in required:
            print('Downloading '+name,flush=True)
            source=folder/name
            url=f'https://huggingface.co/{REPO}/resolve/{REVISION}/{name}?download=true&zyntracut=1'
            with urllib.request.urlopen(url,timeout=120) as response,source.open('wb') as output:
                size=0
                while chunk:=response.read(1024*1024):
                    size+=len(chunk)
                    if size>500_000_000:raise ValueError('Download exceeds model file size limit')
                    output.write(chunk)
                    if name=='model.bin' and size%(25*1024*1024)<1024*1024:
                        print(f'{size//1024**2} MB downloaded',flush=True)
            if name in HASHES:
                with source.open('rb') as file:
                    digest=hashlib.file_digest(file,'sha256').hexdigest()
                if digest!=HASHES[name]:raise ValueError('Model checksum mismatch: '+name)
        import ctranslate2
        import sentencepiece
        sentencepiece.SentencePieceProcessor(model_file=str(folder/'spm.128k.model'))
        engine=ctranslate2.Translator(str(folder),device='cpu',compute_type='int8',intra_threads=2)
        del engine
        destination.mkdir(exist_ok=True)
        for name in required:shutil.move(str(folder/name),str(destination/name))
    print('M2M100 CPU INT8 translation installed. No speech or transcript is sent online.',flush=True)


if __name__=='__main__':main()
