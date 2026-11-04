"""Install the lightweight offline eSpeak NG voice engine in this project only."""
import hashlib
import os
from pathlib import Path
import subprocess
import urllib.request

URL = 'https://github.com/espeak-ng/espeak-ng/releases/download/1.52.0/espeak-ng.msi'
SHA256 = '7f673c709ea5dd579d3b5ebb98688cc575328a6ab7438d2bc405b88cedaeafb9'


def main():
    if os.name != 'nt':
        raise SystemExit('Install espeak-ng with your operating system package manager, or set ESPEAK_NG_BINARY.')
    folder = Path(__file__).resolve().parents[1]/'data/tools/espeak'
    folder.mkdir(parents=True, exist_ok=True)
    package = folder/'espeak-ng-1.52.0.msi'
    if not package.is_file():
        with urllib.request.urlopen(URL, timeout=60) as response:
            data = response.read(20_000_001)
        if len(data) > 20_000_000 or hashlib.sha256(data).hexdigest() != SHA256:
            raise ValueError('Unexpected offline voice package; installation cancelled.')
        package.write_bytes(data)
    if hashlib.sha256(package.read_bytes()).hexdigest() != SHA256:
        raise ValueError('Offline voice package checksum mismatch.')
    runtime = folder/'runtime'
    result = subprocess.run(['msiexec.exe','/a',str(package),'/qn','TARGETDIR='+str(runtime)], timeout=120)
    if result.returncode or not (runtime/'eSpeak NG/espeak-ng.exe').is_file():
        raise RuntimeError('Could not extract the offline voice engine.')
    print('Offline voices installed locally. No cloud service or paid API is used.')


if __name__ == '__main__':
    main()
