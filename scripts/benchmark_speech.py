"""Read-only real-model CPU comparison; never overlap active user jobs."""
import argparse
import json
import time
from pathlib import Path
from faster_whisper import BatchedInferencePipeline,WhisperModel
from faster_whisper.audio import decode_audio
from backend import speech,store

parser=argparse.ArgumentParser()
parser.add_argument('--project-id',help='Compare first 120 seconds of a local project without saving transcript text.')
parser.add_argument('--seconds',type=int,default=120,choices=range(30,301),metavar='30..300')
args=parser.parse_args()
if any(p['status'] in ('queued','transcribing','analyzing') or any(c['status'] in ('queued','rendering') for c in p['clips']) for p in store.all_projects()):
    raise SystemExit('Benchmark deferred: a user job is active. Do not interrupt it.')
sample=decode_audio(str(store.DATA/'jfk.flac'),sampling_rate=16000)
audio=sample
if args.project_id:
    project=store.get(args.project_id)
    assert project,'Unknown local project'
    folder=(store.DATA/project['id']).resolve()
    assert folder.parent==store.DATA.resolve()
    audio=decode_audio(str(folder/'source'),sampling_rate=16000)[:args.seconds*16000]
model=WhisperModel('tiny',device='cpu',compute_type='int8',download_root=str(store.DATA/'models'),local_files_only=True)

def run(waveform,batched):
    started=time.perf_counter()
    if batched:
        segments,info=BatchedInferencePipeline(model=model).transcribe(waveform,batch_size=speech.fast_batch_size(),beam_size=1,temperature=0,vad_filter=True,vad_parameters={'min_silence_duration_ms':500},without_timestamps=False)
    else:
        segments,info=model.transcribe(waveform,beam_size=1,vad_filter=True)
    segments=list(segments)
    assert segments,'No recognized speech in benchmark source'
    # Whisper may predict a cue end beyond EOF. Match the application's
    # source-bound clamping rather than rejecting normal model output.
    duration=len(waveform)/16000
    assert any(0<=s.start<min(s.end,duration) for s in segments)
    return round(time.perf_counter()-started,3)

run(sample,False);run(sample,True)
print('Warm-up complete. Measuring previous sequential decoder…',flush=True)
old=run(audio,False)
print('Measuring batched Fast decoder…',flush=True)
new=run(audio,True)
report={'fixture':f'First {args.seconds} seconds of a local source; transcript text is not saved' if args.project_id else 'Short real JFK speech fixture (does not fill a batch)',
        'audio_seconds':round(len(audio)/16000,3),'device':'CPU','model':'tiny INT8','batch_size':speech.fast_batch_size(),
        'previous_seconds':old,'batched_seconds':new,'measured_speedup':round(old/new,2),
        'limits':'Single warmed-up run per path on this machine; Fast changes context/fallback/VAD behavior and can change recognition accuracy. More RAM may be used. Not a universal speed guarantee.'}
path=Path('artifacts/speech-benchmark.json');path.parent.mkdir(exist_ok=True)
path.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
