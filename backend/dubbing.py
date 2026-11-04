"""Offline, sentence-timed eSpeak dubbing. No voice cloning or mouth animation."""
import hashlib
from contextlib import ExitStack
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import wave

import numpy as np

from . import media, store, translation
from .languages import CAPTION_TARGETS, SPEECH_NAMES

RATE = 22050


def executable():
    configured = os.environ.get('ESPEAK_NG_BINARY')
    local = Path(__file__).resolve().parents[1] / 'data/tools/espeak/runtime/eSpeak NG/espeak-ng.exe'
    return configured or (str(local) if local.is_file() else shutil.which('espeak-ng'))


def command():
    binary = executable()
    if not binary:
        raise ValueError('Offline voice engine is missing. Run python -m scripts.setup_dubbing, then retry.')
    folder = Path(binary).resolve().parent
    return [str(binary), *(['--path='+str(folder)] if (folder/'espeak-ng-data').is_dir() else [])]


def voices():
    if not executable():
        return set()
    result = subprocess.run([*command(), '--voices'], capture_output=True, timeout=10)
    if result.returncode:
        return set()
    codes = set()
    for line in result.stdout.decode('utf-8', errors='replace').splitlines()[1:]:
        parts = line.split()
        # MBROLA entries require an additional engine; don't advertise them.
        if len(parts) >= 5 and not parts[4].startswith(('mb/', 'mb\\')):
            codes.add(parts[1].split('-')[0])
    return codes


def catalog(source):
    available = voices()
    return {'engine':'eSpeak NG', 'installed':bool(available), 'mouth_animation':False,
            'languages':[{'script':script, 'language':code, 'name':SPEECH_NAMES[code],
                          'available':code in available and translation.route_available(source, code)}
                         for script, code in CAPTION_TARGETS.items() if script != 'roman_urdu'],
            'message':'Basic synthetic voice, timed to subtitle sentences. Replaces source audio, including background sounds. Does not clone voices or animate lips.'}


def fingerprint(segments, language):
    data = {'language':language, 'segments':[{k:s[k] for k in ('start','end','text')} for s in segments]}
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def synthesize(text, language, output):
    text_file = output.with_suffix('.txt')
    text_file.write_text(text, encoding='utf-8')
    try:
        result = subprocess.run([*command(), '-v', language, '-s', '165', '-b', '1', '-f', str(text_file), '-w', str(output)],
                                capture_output=True, timeout=30)
        if result.returncode or not output.is_file():
            raise ValueError('Offline speech synthesis failed: '+result.stderr.decode('utf-8', errors='replace')[-300:])
    finally:
        text_file.unlink(missing_ok=True)


def create_track(segments, language, duration, output, progress=None):
    """Disk-backed mono PCM; each utterance ends inside its original sentence slot."""
    if language not in voices():
        raise ValueError('No installed offline voice supports the selected language.')
    total = math.ceil(duration * RATE)
    with ExitStack() as stack:
        temporary=stack.enter_context(tempfile.TemporaryDirectory(prefix='zyntra-dub-', dir=output.parent))
        folder = Path(temporary)
        samples = np.memmap(folder/'timeline.pcm', dtype='<i2', mode='w+', shape=(total,))
        stack.callback(samples._mmap.close)
        samples[:] = 0
        previous_end = 0
        for index, segment in enumerate(segments):
            start = max(0, round(segment['start'] * RATE), previous_end)
            end = min(total, round(segment['end'] * RATE))
            if not segment['text'].strip():
                continue
            if end <= start:
                raise ValueError('Overlapping subtitle sentences leave no room for a dubbed voice. Correct their timestamps first.')
            raw = folder/'raw.wav'
            fitted = folder/'fitted.wav'
            synthesize(segment['text'], language, raw)
            with wave.open(str(raw), 'rb') as audio:
                spoken_duration = audio.getnframes()/audio.getframerate()
            slot = (end-start)/RATE
            tempo = max(1, spoken_duration/slot)
            if tempo > 2.5:
                raise ValueError(f'Subtitle {index+1} is too long to speak clearly in its time slot. Shorten the translation or adjust its timestamps.')
            filters = []
            while tempo > 2:
                filters.append('atempo=2')
                tempo /= 2
            if tempo > 1:
                filters.append(f'atempo={tempo:.8f}')
            filters += [f'apad,atrim=duration={slot:.8f}', 'alimiter=limit=0.9:level=disabled']
            media.run(['-i',str(raw),'-af',','.join(filters),'-ac','1','-ar',str(RATE),'-c:a','pcm_s16le',str(fitted)], timeout=60)
            with wave.open(str(fitted), 'rb') as audio:
                data = np.frombuffer(audio.readframes(end-start), dtype='<i2')
                samples[start:start+len(data)] = data
            previous_end = end
            if progress:
                progress(index+1, len(segments))
        with wave.open(str(output), 'wb') as audio:
            audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(RATE)
            for start in range(0, total, RATE*30):
                audio.writeframes(samples[start:start+RATE*30].tobytes())


def audio_for_project(project, folder):
    dub = project.get('dubbing', {})
    if not dub.get('enabled'):
        return None
    if dub.get('status') != 'ready' or dub.get('fingerprint') != fingerprint(project['transcript'], dub.get('language')):
        raise ValueError('Translated voice is out of date. Regenerate it in Transcript, or choose Original audio before rendering.')
    path = (folder/dub.get('file','')).resolve()
    if path.parent != folder.resolve() or not path.is_file():
        raise ValueError('Translated voice file is missing. Regenerate it in Transcript.')
    return path
