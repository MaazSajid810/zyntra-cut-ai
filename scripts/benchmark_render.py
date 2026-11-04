"""Compare the previous 720p render path with the new Fast 480p profile."""
import json
import tempfile
import time
from pathlib import Path
from backend import media

with tempfile.TemporaryDirectory(prefix='clipforge-speed-') as tmp:
    folder=Path(tmp)
    source=folder/'source.mp4'
    media.run(['-f','lavfi','-i','testsrc2=size=640x360:rate=30','-f','lavfi','-i','sine=frequency=440:sample_rate=48000','-t','12','-c:v','libx264','-preset','ultrafast','-c:a','aac',str(source)])
    segments=[{'start':0,'end':12,'text':'A real render speed test with burned-in subtitles'}]
    media.write_ass(folder/'old.ass',segments,0,12,'mint',720,1280)
    started=time.perf_counter()
    media.run(['-i',str(source),'-t','12','-vf','scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,setsar=1,ass=old.ass','-c:v','libx264','-preset','veryfast','-crf','21','-pix_fmt','yuv420p','-c:a','aac','-movflags','+faststart',str(folder/'old.mp4')],cwd=folder)
    old=time.perf_counter()-started
    started=time.perf_counter()
    media.render(source,folder,{'id':'fast','start':0,'end':12,'aspect':'vertical','style':'mint','render_quality':'fast'},segments,folder/'fast.mp4')
    fast=time.perf_counter()-started
    results={'input':'12-second 640x360 30fps generated test video','previous_720p_seconds':round(old,3),'fast_480p_seconds':round(fast,3),'ratio_previous_to_fast':round(old/fast,2),'tradeoff':'Fast uses 480p and a faster encoder; this is not equal-quality benchmarking. Results depend on the machine and source.'}
    output=Path('artifacts/render-benchmark.json')
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(json.dumps(results,indent=2))
