"""Bounded source measurements, not emotion recognition or view prediction."""
import math
import os
import tempfile
import time
from pathlib import Path

import numpy as np
import av

from . import media

VERSION = 2
LONG_SOURCE_SECONDS = 180
VISUAL_BUDGET_SECONDS = 60


def keyframe_visuals(source,duration):
    """Use actual keyframe presentation times instead of decoding every frame.

    The sparse measurements describe keyframe changes, not precise scene cuts.
    Missing/unscanned intervals never receive invented activity measurements.
    """
    values,times,scenes=[],[],[]
    previous=None
    started=time.monotonic()
    complete=True
    with av.open(str(source)) as container:
        stream=container.streams.video[0]
        stream.codec_context.skip_frame='NONKEY'
        stream.codec_context.thread_count=max(1,min(4,os.cpu_count() or 1))
        offset=float(container.start_time or 0)/av.time_base
        def append_frame(frame):
            nonlocal previous
            if not frame.key_frame or frame.pts is None:return
            # Delayed H.264 frames returned by codec flush can lack a frame
            # time_base; their PTS still uses the demuxed stream's time base.
            time_base=frame.time_base or stream.time_base
            if not time_base:return
            moment=max(0,float(frame.pts*time_base)-offset)
            if moment>duration:return
            image=frame.reformat(width=160,height=90,format='gray').to_ndarray().astype(np.float32)
            change=float(np.mean(np.abs(image-previous))/255) if previous is not None else 0
            times.append(round(moment,3));values.append(round(change,4))
            if change>=.18 and len(scenes)<5000:scenes.append(round(moment,3))
            previous=image
        # Some decoders (including this VP9 build) ignore skip_frame. Reject
        # non-key packets before decode so they cannot consume the full budget.
        for packet in container.demux(stream):
            if time.monotonic()-started>VISUAL_BUDGET_SECONDS:
                complete=False
                break
            if not packet.is_keyframe:continue
            for frame in packet.decode():append_frame(frame)
        if complete:
            for frame in stream.codec_context.decode(None):append_frame(frame)
    return values,times,scenes,complete


def inspect_source(source, duration, has_audio=True):
    duration = float(duration)
    # Small raw files avoid accumulating full-resolution video/audio in RAM.
    with tempfile.TemporaryDirectory(prefix='zyntra-analysis-') as temporary:
        folder = Path(temporary)
        video, audio = folder/'visual.gray', folder/'audio.pcm'
        sparse=duration>LONG_SOURCE_SECONDS
        times=None;complete=True
        if sparse:
            visual,times,scenes,complete=keyframe_visuals(source,duration)
            if has_audio:
                media.run(['-threads','2','-i',str(source),'-map','0:a:0','-vn',
                           '-af','aresample=8000:async=1:first_pts=0','-ac','1','-ar','8000',
                           '-c:a','pcm_s16le','-f','s16le',str(audio)],timeout=300)
        else:
            args = ['-threads','1','-i',str(source),'-map','0:v:0','-an',
                    '-vf','fps=2:start_time=0,scale=160:90,format=gray',
                    '-threads','1','-f','rawvideo',str(video)]
            if has_audio:
                args += ['-map','0:a:0','-vn','-af','aresample=8000:async=1:first_pts=0',
                         '-ac','1','-ar','8000','-c:a','pcm_s16le','-f','s16le',str(audio)]
            media.run(args, timeout=120)
            visual,scenes,previous=[],[],None
            with video.open('rb') as stream:
                while data := stream.read(160*90):
                    if len(data) != 160*90: break
                    frame = np.frombuffer(data,dtype=np.uint8).astype(np.float32)
                    change = float(np.mean(np.abs(frame-previous))/255) if previous is not None else 0
                    visual.append(round(change,4))
                    if change >= .18 and len(scenes)<5000: scenes.append(round((len(visual)-1)*.5,3))
                    previous = frame
        levels = []
        if has_audio:
            with audio.open('rb') as stream:
                while data := stream.read(8000):  # 0.5s, mono 8kHz signed 16-bit
                    samples=np.frombuffer(data[:len(data)//2*2],dtype='<i2').astype(np.float32)/32768
                    if len(samples):levels.append(round(20*math.log10(max(1e-6,float(np.sqrt(np.mean(samples*samples))))),2))
        if has_audio:
            # Pad trailing silence rather than stretching shorter audio to fit video.
            count=math.ceil(duration/.5)
            levels=levels[:count]+[-120.0]*max(0,count-len(levels))
        silences, beginning = [], None
        for i,level in enumerate([*levels,0]):
            if level < -38 and beginning is None: beginning=i*.5
            if level >= -38 and beginning is not None:
                end=min(i*.5,duration)
                if end-beginning>=.5:silences.append([round(beginning,3),round(end,3)])
                beginning=None
        # One waveform peak per display bucket; maxima retain short transients.
        step=max(1,math.ceil(len(levels)/1200))
        waveform=[round(max(10**(v/20) for v in levels[i:i+step]),4) for i in range(0,len(levels),step)]
        result={'version':VERSION,'duration':duration,'sample_seconds':.5,
                'audio_db':levels,'visual_change':visual,'scene_changes':scenes,'silences':silences,
                'waveform':waveform,'waveform_step':step*.5,
                'limitations':'Visual changes sampled at 2 fps; silence uses a -38 dBFS threshold. Audio level is not emotion or speech recognition. No face tracking or calibrated virality prediction.'}
        if sparse:
            result.update(visual_sample_times=times,visual_sample_mode='keyframes',visual_scan_complete=complete,
                          limitations='Visual changes sampled at encoded keyframes with actual presentation times; fine scene cuts between keyframes can be missed. '+
                          ('' if complete else 'The visual scan reached its time budget; unscanned intervals have no visual measurement. ')+
                          'Full audio energy/silence uses 0.5-second intervals. Audio level is not emotion or speech recognition. No face tracking or calibrated virality prediction.')
        return result


def interval_evidence(analysis,start,end):
    step=analysis.get('sample_seconds',.5)
    low,high=max(0,int(start/step)),max(1,math.ceil(end/step))
    levels=analysis.get('audio_db',[])[low:high]
    if 'visual_sample_times' in analysis:
        visual=[value for moment,value in zip(analysis['visual_sample_times'],analysis.get('visual_change',[])) if start<=moment<end]
    else:
        visual=analysis.get('visual_change',[])[low:high]
    silence=sum(max(0,min(end,b)-max(start,a)) for a,b in analysis.get('silences',[]))
    return {'audio_energy':round(min(100,max(0,(float(np.mean(levels))+45)/35*100))) if levels else None,
            'visual_activity':round(min(100,float(np.mean(visual))/.12*100)) if visual else None,
            'silence_fraction':round(min(1,silence/max(.001,end-start)),3),
            'scene_changes':sum(start<=t<end for t in analysis.get('scene_changes',[]))}
