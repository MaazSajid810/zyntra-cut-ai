"""Install official Argos translation packages locally (one-time download).
Models: https://github.com/argosopentech/argospm-index
Default: existing English/Urdu/Hindi packages. Add Spanish with --languages es.
"""
import argparse
import hashlib
import json
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from backend.translation import ROOT,PAIRS,pair_installed


def selected_pairs(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    choice=parser.add_mutually_exclusive_group()
    choice.add_argument('--languages',nargs='+',help='Language codes to install in both directions with English (for example es fr).')
    choice.add_argument('--pairs',nargs='+',help='Explicit directions such as en:es es:en.')
    args=parser.parse_args(argv)
    if args.languages:
        pairs=[pair for language in args.languages for pair in (('en',language),(language,'en'))]
    elif args.pairs:
        pairs=[tuple(pair.split(':')) for pair in args.pairs]
    else:pairs=[('en','ur'),('ur','en'),('en','hi'),('hi','en')]
    for pair in pairs:
        if pair not in PAIRS:parser.error(f'No verified Argos package is configured for {":".join(pair)}; native speech captions remain available.')
    return list(dict.fromkeys(pairs))


def main(argv=None):
    pairs=selected_pairs(argv)
    ROOT.mkdir(parents=True,exist_ok=True)
    for source,target in pairs:
        version=PAIRS[source,target]
        destination=ROOT/f'{source}_{target}'
        if pair_installed(source,target):
            print(f'{source} -> {target}: already installed',flush=True);continue
        mirror_hash={('en','ur'):'5ca67bf37de95941e0eb8b6ad07db197023d13290ab5bd61851d3edc31f0a859',('ur','en'):'0d722bb7c4686a58ad1361202b192294cb939518d6f851741e68b36bb2e56d73',('en','hi'):'60470a003a9c7339db8c060ed8eafc7cf999ba90dfa5dceebd8d0a4f75f1d3f0',('hi','en'):'f99eadf297073c0f5a320df5d634ebb73e9ab0b819404edf7bd0a0daf6b1ce43',
                     ('en','es'):'d698d0ef87ad70d5d184b7fa6965905bf4368f09a2bb9ffb165a79bac96af0c4',
                     ('es','en'):'c54df2b62fceaf54a3ce5d97db6bf56efd7940063329f6778f4212d2acb370d4'}
        filename=f'translate-{source}_{target}-{version}.argosmodel'
        revision='c57c8db597a5607fc23f21af7c9449d2cc7cc332' if (source,target)==('en','hi') else '52632ee42da594912409d9a2ccc601984385de4d'
        if (source,target) in (('en','es'),('es','en')):
            revision='0fbbd0e16e6b24c56685217b8a0b3bbffc9775c7'
            filename=f'{source}_{target}.argosmodel'
        url=(f'https://huggingface.co/TiberiuCristianLeon/Argostranslate/resolve/{revision}/{filename}'
             if (source,target) in mirror_hash else f'https://argos-net.com/v1/{filename}')
        print(f'Downloading {source} -> {target}...',flush=True)
        with tempfile.TemporaryDirectory(dir=ROOT,prefix='install-') as temp:
            folder=Path(temp);archive=folder/'package.zip'
            with urllib.request.urlopen(url,timeout=120) as response,archive.open('wb') as output:
                total=0
                while chunk:=response.read(1024*1024):
                    total+=len(chunk)
                    if total>500_000_000:raise ValueError('Translation download exceeds the 500 MB package limit')
                    output.write(chunk)
            digest=hashlib.sha256(archive.read_bytes()).hexdigest()
            if (source,target) in mirror_hash and digest!=mirror_hash[source,target]:raise ValueError('Translation package checksum mismatch')
            with zipfile.ZipFile(archive) as package:
                members=package.infolist()
                if sum(m.file_size for m in members)>2_000_000_000:raise ValueError('Translation package too large')
                unpack=folder/'unpacked'
                for member in members:
                    resolved=(unpack/member.filename).resolve()
                    if not resolved.is_relative_to(unpack.resolve()):raise ValueError('Unsafe model package path')
                package.extractall(unpack)
            candidates=list(unpack.rglob('metadata.json'))
            if len(candidates)!=1:raise ValueError('Expected exactly one translation metadata file')
            metadata=candidates[0]
            model_folder=metadata.parent
            info=json.loads(metadata.read_text(encoding='utf-8'))
            if info['from_code']!=source or info['to_code']!=target:raise ValueError('Unexpected translation language pair')
            if not (model_folder/'sentencepiece.model').exists():raise ValueError('Unsupported tokenizer package')
            if not (model_folder/'model'/'model.bin').exists():raise ValueError('Translation package has no CTranslate2 model')
            if destination.exists():raise ValueError(f'An incomplete model directory exists: {destination}. Inspect it before retrying; it was not overwritten.')
            (model_folder/'source.json').write_text(json.dumps({'source':url,'sha256':digest},indent=2))
            shutil.move(str(model_folder),str(destination))
        print(f'{source} -> {target}: installed',flush=True)


if __name__=='__main__':main()
