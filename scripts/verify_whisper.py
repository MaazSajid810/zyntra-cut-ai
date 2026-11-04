"""Optional real-model smoke test; downloads an actual speech fixture and model."""
import json
import urllib.request

from backend import media, store
from faster_whisper import WhisperModel

path = store.DATA / 'jfk.flac'
if not path.exists():
    urllib.request.urlretrieve('https://raw.githubusercontent.com/openai/whisper/main/tests/jfk.flac', path)
model = WhisperModel('base', device='cpu', compute_type='int8', download_root=str(store.DATA / 'models'))
segments, info = model.transcribe(str(path), vad_filter=True)
transcript = [{'start': s.start, 'end': s.end, 'text': s.text} for s in segments]
text = ' '.join(s['text'] for s in transcript)
assert 'country' in text.lower(), text
print(json.dumps({'language': info.language, 'text': text, 'highlights': media.highlights(transcript, info.duration)}, indent=2))
