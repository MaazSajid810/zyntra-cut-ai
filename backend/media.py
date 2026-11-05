import os
import math
import re
import subprocess
import time
from pathlib import Path

import av
import imageio_ffmpeg
from . import captions,compositor

FFMPEG = os.environ.get('FFMPEG_BINARY') or imageio_ffmpeg.get_ffmpeg_exe()
FONTS = Path(__file__).resolve().parents[1]/'frontend'/'public'/'fonts'

def run(args, cwd=None, timeout=1800):
    for attempt in range(4):
        try:
            result = subprocess.run([FFMPEG, '-hide_banner', '-loglevel', 'error', '-y', *args], cwd=cwd, capture_output=True, text=True, timeout=timeout)
            break
        except PermissionError as exc:
            # Windows can transiently lock the executable during concurrent
            # launches. Retry failed starts only, never an encoding error.
            if getattr(exc,'winerror',None) not in (5,32) or attempt==3:
                raise
            time.sleep(.2*(attempt+1))
    if result.returncode:
        raise RuntimeError('FFmpeg: ' + result.stderr[-1500:])

def probe(path):
    with av.open(str(path)) as container:
        videos = list(container.streams.video)
        if not videos:
            raise ValueError('This file has no video stream.')
        stream = videos[0]
        duration = float(container.duration / av.time_base) if container.duration else float((stream.duration or 0) * stream.time_base)
        if duration <= 0 or duration > 14400:
            raise ValueError('Video must have a known duration between 0 and 4 hours.')
        return {'duration': duration, 'width': stream.width, 'height': stream.height, 'has_audio': bool(container.streams.audio)}

def highlights(segments, duration, target=35, limit=5, exclude=(), min_duration=None, max_duration=None):
    """Deterministic extractive ranking, not an LLM or a virality prediction."""
    candidates = []
    hooks = {'why', 'how', 'secret', 'mistake', 'never', 'imagine', 'learn', 'because', 'discovered', 'surprising', 'best'}
    desired = min(max_duration,max(min_duration or 0,target)) if max_duration is not None else target
    for index, segment in enumerate(segments):
        start = segment['start']
        end = segment['end']
        selected = []
        for item in segments[index:]:
            if max_duration is not None and item['end'] - start > max_duration:
                break
            if max_duration is None and item['end'] - start > target + 15 and selected:
                break
            selected.append(item)
            end = item['end']
            if end - start >= desired:
                break
        minimum = (min_duration if duration>=min_duration else duration*.7) if min_duration is not None else min(8,duration*.7)
        if not selected or end - start < minimum:
            continue
        text = ' '.join(s['text'] for s in selected).strip()
        words = re.findall(r"\b[\w']+\b", text.lower())
        signals = len(set(words) & hooks)
        density = min(1, len(words) / max(1, end-start) / 2.5)
        score = round(min(99, 40 + signals * 6 + density * 20 + (8 if '?' in text else 0) + (5 if text.endswith(('.', '!', '?')) else 0)))
        candidates.append({'start': round(start, 3), 'end': round(min(end, duration), 3), 'title': ' '.join(text.split()[:9]) or 'Highlight', 'score': score, 'reason': f'{signals} hook words · {len(words)} words · speech density {density:.0%}'})
    chosen = []
    for candidate in sorted(candidates, key=lambda c: c['score'], reverse=True):
        if all(candidate['end'] <= c['start'] or candidate['start'] >= c['end'] for c in [*chosen, *exclude]):
            chosen.append(candidate)
        if len(chosen) >= limit:
            break
    return sorted(chosen, key=lambda c: c['start'])

def stamp(seconds):
    centis = math.floor(max(0, seconds) * 100 + .5 + 1e-8)
    return f'{centis//360000}:{centis//6000%60:02}:{centis//100%60:02}.{centis%100:02}'

def shifted_captions(segments, offset):
    # Offset is measured in output seconds; callers convert to source seconds.
    return [{**s,'start':s['start']+offset,'end':s['end']+offset,
             'words':[{**w,'start':w['start']+offset,'end':w['end']+offset} for w in s.get('words',[])]} for s in segments]


def subtitle_file(segments, kind='srt', start=0, end=float('inf'), speed=1, offset=0):
    def timestamp(seconds):
        ms = math.floor(max(0,seconds)*1000 + .5 + 1e-8)
        return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02}{"," if kind=="srt" else "."}{ms%1000:03}'
    cues = []
    for s in shifted_captions(segments,offset*speed):
        a,b=max(start,s['start']),min(end,s['end'])
        if b<=a:
            continue
        text=s['text'].replace('\r',' ').replace('\n',' ').replace('-->','→')
        cues.append(f'{len(cues)+1}\n{timestamp((a-start)/speed)} --> {timestamp((b-start)/speed)}\n{text}\n')
    return ('WEBVTT\n\n' if kind=='vtt' else '')+'\n'.join(cues)

def literal_text(text):
    return text.replace('\\', '／').replace('{', '(').replace('}', ')').replace('\r', ' ').replace('\n', ' ')


def readable_cues(segment):
    """Short readable phrases; timing within a segment is estimated, not word alignment."""
    groups=[]
    current=[]
    for word in segment['text'].split():
        if current and (len(current)>=7 or len(' '.join([*current,word]))>42):
            groups.append(' '.join(current));current=[]
        current.append(word)
    if current:groups.append(' '.join(current))
    total=sum(len(text) for text in groups) or 1
    offset=0
    for text in groups:
        a=segment['start']+(segment['end']-segment['start'])*offset/total
        offset+=len(text)
        b=segment['start']+(segment['end']-segment['start'])*offset/total
        yield {'start':a,'end':b,'text':text}

def write_ass(path, segments, start, end, style, width, height, options=None):
    options = options or {}
    speed = options.get('speed',1)
    segments=shifted_captions(segments,options.get('caption_offset',0)*speed)
    colors = {'mint':'&H0076F2C5', 'yellow':'&H003BEFFF', 'neon':'&H00F178FC','cyan':'&H00FFE655','orange':'&H00111111','comic':'&H003BEFFF'}
    color = colors.get(style, '&H00FFFFFF')
    if options.get('subtitle_color'):
        rgb = options['subtitle_color'].lstrip('#')
        color = '&H00' + rgb[4:6] + rgb[2:4] + rgb[0:2]
    font_size = max(12, round(options.get('subtitle_size', 34) * width / 720))
    alignment = {'bottom':2, 'center':5, 'top':8}[options.get('subtitle_position', 'bottom')]
    overlay_alignment = {'bottom':2, 'center':5, 'top':8}[options.get('overlay_position', 'top')]
    border = 3 if style in ('boxed','orange','red') else 1
    outline = {'minimal':0,'comic':5,'elegant':1,'shadow':1}.get(style,3)
    outline_color = {'orange':'&H003399FF','red':'&H003333DD','cyan':'&H00332211'}.get(style,'&H00111111')
    italic = -1 if style=='elegant' else 0
    shadow = 4 if style=='shadow' else 1
    glow_rgb=options.get('highlight_color','#25f5d0') if style=='neon_highlight' else options.get('subtitle_color') or '#fc78f1'
    glow_rgb=glow_rgb.lstrip('#')
    glow_color='&H00'+glow_rgb[4:6]+glow_rgb[2:4]+glow_rgb[:2]
    font = options.get('subtitle_font', 'Arial')
    if any(re.search(r'[\u0600-\u06ff]',s['text']) for s in segments):
        font = 'Noto Sans Arabic'
    if any(re.search(r'[\u0900-\u097f]',s['text']) for s in segments) or re.search(r'[\u0900-\u097f]',options.get('overlay_text','')):
        font = 'Noto Sans Devanagari'
    if any(re.search(r'[\u0a00-\u0a7f]',s['text']) for s in segments) or re.search(r'[\u0a00-\u0a7f]',options.get('overlay_text','')):
        font = 'Noto Sans Gurmukhi'
    if any(re.search(r'[\u0980-\u09ff]',s['text']) for s in segments) or re.search(r'[\u0980-\u09ff]',options.get('overlay_text','')):
        font = 'Noto Sans Bengali'
    margin = round(height * .14)
    sticker = options.get('sticker','none') if options.get('sticker_enabled',False) else 'none'
    sticker_color = {'subscribe':'&H003030DD','follow':'&H00C05060','like':'&H009040D0'}.get(sticker,'&H00111111')
    sticker_size = max(12,round(options.get('sticker_size',30)*width/720))
    sticker_alignment = {'top-left':7,'top-right':9,'bottom-left':1,'bottom-right':3}[options.get('sticker_position','top-right')]
    header = f'''[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{font_size},{color},&H000000FF,{outline_color},&H88000000,-1,{italic},0,0,100,100,0,0,{border},{outline},{shadow},{alignment},25,25,{margin},1
Style: Glow,{font},{font_size},{glow_color},&H000000FF,{glow_color},{glow_color},-1,{italic},0,0,100,100,0,0,1,5,0,{alignment},25,25,{margin},1
Style: Overlay,{font},{font_size},{color},&H000000FF,&H00111111,&H88000000,-1,0,0,0,100,100,0,0,1,3,1,{overlay_alignment},25,25,{margin},1
Style: Sticker,Poppins,{sticker_size},&H00FFFFFF,&H000000FF,{sticker_color},{sticker_color},-1,0,0,0,100,100,0,0,3,8,0,{sticker_alignment},25,25,25,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    events = []
    mode=options.get('caption_mode','phrase')
    if style!='none' and mode!='phrase':
        rgb=options.get('highlight_color','#ffdf35').lstrip('#')
        highlight='&H'+rgb[4:6]+rgb[2:4]+rgb[:2]
        prepared=[{**s,'text':s['text'].upper(),'words':[{**w,'word':w['word'].upper()} for w in s.get('words',[])]} if options.get('subtitle_uppercase') else s for s in segments]
        events.extend(captions.events(prepared,start,end,speed,mode,options.get('caption_animation','pop'),highlight,literal_text,stamp,neon_highlight=style=='neon_highlight'))
        segments=[s for s in segments if not captions.aligned(s)]
    for segment in (cue for source in segments for cue in readable_cues(source)):
        if style == 'none':
            break
        a, b = max(start, segment['start']), min(end, segment['end'])
        if b <= a:
            continue
        # Strip ASS control characters so editable text is always literal.
        text = literal_text(segment['text'])
        if options.get('subtitle_uppercase'):
            text = text.upper()
        events.append(f'Dialogue: 0,{stamp((a-start)/speed)},{stamp((b-start)/speed)},Default,,0,0,0,,{text}\n')
    if style in ('neon','neon_highlight'):
        glow_events=[]
        for event in events:
            parts=event.rstrip('\n').split(',',9)
            if parts[3]!='Default' or style=='neon_highlight' and r'\3c' in parts[9]:
                continue
            parts[0]='Dialogue: -1'
            parts[3]='Glow'
            parts[9]=r'{\blur4}'+parts[9].replace(r'{\rDefault}',r'{\rGlow\blur4}')
            glow_events.append(','.join(parts)+'\n')
        events=glow_events+events
    if options.get('overlay_text'):
        events.append(f"Dialogue: 1,{stamp(0)},{stamp((end-start)/speed)},Overlay,,0,0,0,,{literal_text(options['overlay_text'])}\n")
    if sticker != 'none':
        length=(end-start)/speed
        timing=options.get('sticker_timing','full')
        hold=min(length,options.get('sticker_duration',3))
        a={'full':0,'start':0,'middle':max(0,(length-hold)/2),'end':max(0,length-hold),'custom':options.get('sticker_at',0)}[timing]
        b=length if timing=='full' else min(length,a+hold)
        animation=options.get('sticker_animation','none')
        tags={'none':'','fade':r'{\fad(180,180)}','pop':r'{\fscx60\fscy60\t(0,120,\fscx110\fscy110)\t(120,220,\fscx100\fscy100)}'}
        tag=tags.get(animation,'')
        if animation=='slide':
            right=options.get('sticker_position','top-right').endswith('right')
            bottom=options.get('sticker_position','top-right').startswith('bottom')
            x=width-25 if right else 25;y=height-25 if bottom else 25
            tag=rf'{{\move({x},{y+50},{x},{y},0,220)\fad(80,120)}}'
        if b>a:events.append(f"Dialogue: 2,{stamp(a)},{stamp(b)},Sticker,,0,0,0,,{tag}{sticker.upper()}\n")
    if options.get('watermark_enabled') and options.get('watermark_text') and options.get('watermark_opacity',.18)>0:
        from PIL import ImageFont
        watermark=options['watermark_text'].replace('\n',' ')
        font_file=FONTS/('NotoSansDevanagari.ttf' if re.search(r'[\u0900-\u097f]',watermark) else 'NotoSansGurmukhi.ttf' if re.search(r'[\u0a00-\u0a7f]',watermark) else 'NotoSansBengali.ttf' if re.search(r'[\u0980-\u09ff]',watermark) else 'NotoSansArabic.ttf' if re.search(r'[\u0600-\u06ff]',watermark) else 'Poppins-Bold.ttf')
        if not font_file.exists():font_file=FONTS/'Poppins-Regular.ttf'
        size=max(10,round(options.get('watermark_size',72)*width/720))
        measured=ImageFont.truetype(str(font_file),size)
        natural=measured.getlength(watermark)
        size=max(8,int(size*min(1,width*.9/max(1,natural))))
        measured=ImageFont.truetype(str(font_file),size)
        text_width=measured.getlength(watermark)
        x=max(0,width-text_width)*options.get('watermark_x',50)/100
        y=max(0,height-size*1.5)*options.get('watermark_y',50)/100
        alpha=round((1-options.get('watermark_opacity',.18))*255)
        rgb=options.get('watermark_color','#ffffff').lstrip('#')
        color=f'&H{rgb[4:6]}{rgb[2:4]}{rgb[:2]}&'
        family='Noto Sans Devanagari' if 'Devanagari' in font_file.name else 'Noto Sans Gurmukhi' if 'Gurmukhi' in font_file.name else 'Noto Sans Bengali' if 'Bengali' in font_file.name else 'Noto Sans Arabic' if 'Arabic' in font_file.name else 'Poppins'
        tag=rf'{{\an7\pos({x:.2f},{y:.2f})\fn{family}\fs{size}\1c{color}\alpha&H{alpha:02X}&\bord0\shad0}}'
        events.append(f'Dialogue: 3,0:00:00.00,{stamp((end-start)/speed)},Default,,0,0,0,,{tag}{literal_text(watermark)}\n')
    Path(path).write_text(header + ''.join(events), encoding='utf-8')

def render(source, directory, clip, segments, output,assets=None,audio_source=None):
    info = probe(source)
    speed = clip.get('speed',1)
    duration = clip['end']-clip['start']
    quality = clip.get('render_quality', 'standard')
    size = {'fast':480, 'standard':720, 'high':1080}[quality]
    ratios = {'vertical':(9,16), 'square':(1,1), 'landscape':(16,9), 'portrait':(4,5)}
    if clip['aspect'] in ratios:
        x, y = ratios[clip['aspect']]
        width = round(size * x / min(x,y) / 2) * 2
        height = round(size * y / min(x,y) / 2) * 2
    else:
        factor = 1 if quality=='high' else min(1, size*16/9/max(info['width'],info['height']))
        width, height = max(2,round(info['width']*factor/2)*2), max(2,round(info['height']*factor/2)*2)
    # Crop at source resolution first, avoiding a large unnecessary upscale.
    crop_width = max(2,int(min(info['width'],info['height']*width/height)/2)*2)
    crop_height = max(2,int(min(info['height'],info['width']*height/width)/2)*2)
    if clip.get('framing', 'fit') == 'fit':
        # Preserve the entire source, including faces/webcams near its edges.
        filters = f'scale={width}:{height}:force_original_aspect_ratio=decrease:force_divisible_by=2,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1'
    else:
        left = int((info['width']-crop_width)*clip.get('crop_x',50)/100/2)*2
        top = int((info['height']-crop_height)*clip.get('crop_y',50)/100/2)*2
        filters = f'crop={crop_width}:{crop_height}:{left}:{top},scale={width}:{height},setsar=1'
    if clip.get('hide_webcam', False):
        # Cover in SOURCE coordinates before reframing, so every output ratio
        # and horizontal mirroring hides the same selected source region.
        left = int(info['width']*clip.get('webcam_x',75)/100)
        top = int(info['height']*clip.get('webcam_y',0)/100)
        right = min(info['width'], math.ceil(info['width']*(clip.get('webcam_x',75)+clip.get('webcam_width',25))/100))
        bottom = min(info['height'], math.ceil(info['height']*(clip.get('webcam_y',0)+clip.get('webcam_height',35))/100))
        filters = f'drawbox=x={left}:y={top}:w={right-left}:h={bottom-top}:color=black:t=fill,' + filters
    if clip.get('cover_source_captions'):
        top=int(info['height']*clip.get('source_caption_y',75)/100)
        band=math.ceil(info['height']*clip.get('source_caption_height',25)/100)
        filters=f'drawbox=x=0:y={top}:w=iw:h={band}:color=black:t=fill,'+filters
    video_effects = {
        'none':'', 'vivid':'eq=saturation=1.5:contrast=1.08',
        # Include midtones: shadow-only adjustments leave neutral gray unchanged.
        'warm':'colorbalance=rs=.08:rm=.18:rh=.06:bs=-.06:bm=-.14:bh=-.04,eq=saturation=1.08',
        'cool':'colorbalance=bs=.08:bm=.18:bh=.06:rs=-.06:rm=-.12:rh=-.04',
        'mono':'hue=s=0',
        'vintage':'eq=saturation=.65:contrast=1.08:brightness=.02,colorchannelmixer=rr=.393:rg=.769:rb=.189:gr=.349:gg=.686:gb=.168:br=.272:bg=.534:bb=.131,vignette=angle=PI/5',
        'mirror':'hflip',
        'cinematic':'eq=contrast=1.12:saturation=.82,colorbalance=bs=.06:rh=.05',
        'sepia':'colorchannelmixer=rr=.393:rg=.769:rb=.189:gr=.349:gg=.686:gb=.168:br=.272:bg=.534:bb=.131',
        'soft':'gblur=sigma=.65,eq=brightness=.025:contrast=.96',
        'sharpen':'unsharp=5:5:.8:5:5:0',
        'blur':'gblur=sigma=3',
    }
    if video_effects[clip.get('video_effect','none')]:
        filters += ',' + video_effects[clip.get('video_effect','none')]
    if clip.get('zoom','none')!='none':
        amount=.035 if clip['zoom']=='gentle' else .08
        filters+=f",scale=w='trunc({width}*(1+{amount}*(1-cos(2*PI*t/6)))/2)*2':h='trunc({height}*(1+{amount}*(1-cos(2*PI*t/6)))/2)*2':eval=frame,crop={width}:{height}"
    # Trim in source time before accelerating; captions use output time.
    filters += f',trim=duration={duration},setpts=(PTS-STARTPTS)/{speed}'
    if speed != 1:
        filters += ',fps=30'
    post_filters=''
    if clip['style'] != 'none' or clip.get('overlay_text') or clip.get('watermark_enabled') or (clip.get('sticker_enabled') and clip.get('sticker','none') != 'none'):
        ass = f"{clip['id']}-{output.stem}.ass"
        write_ass(directory / ass, segments, clip['start'], clip['end'], clip['style'], width, height, clip)
        fonts_path=FONTS.as_posix().replace(':',r'\:').replace("'",r"'\''")
        post_filters = f"ass={ass}:fontsdir='{fonts_path}'"
    args = ['-ss', str(clip['start']), '-i', str(source)]
    audio_index=0
    if audio_source:
        args+=['-ss',str(clip['start']),'-i',str(audio_source)]
        audio_index=1
    voice = clip.get('voice_effect','none')
    audio_filter=None
    if voice != 'mute':
        voice_filters = {'none':'', 'deep':'aresample=48000,asetrate=38400,aresample=48000,atempo=1.25', 'high':'aresample=48000,asetrate=60000,aresample=48000,atempo=.8', 'radio':'highpass=f=300,lowpass=f=3000', 'echo':'aecho=.8:.7:80:.25'}
        strength=clip.get('voice_strength',.5)
        if voice in ('deep','high'):
            ratio=1-.4*strength if voice=='deep' else 1+.5*strength
            voice_filters[voice]=f'aresample=48000,asetrate={round(48000*ratio)},aresample=48000,atempo={1/ratio}'
        if info['has_audio'] or audio_source:
            # Keep delayed audio and gaps on the same timeline as the picture.
            audio = ['aresample=48000:async=1:first_pts=0',f'atrim=duration={duration}','asetpts=PTS-STARTPTS']
            if clip.get('denoise'):audio.append('afftdn=nf=-25')
            if clip.get('audio_leveling'):audio.append('loudnorm=I=-16:TP=-1.5:LRA=11')
            if voice_filters[voice]:
                audio.append(voice_filters[voice])
            # Chain factors <=2 to avoid atempo's sample skipping above 2x.
            tempo = speed
            while tempo > 2:
                audio.append('atempo=2')
                tempo /= 2
            if tempo != 1:
                audio.append(f'atempo={tempo}')
            audio_filter=','.join([*audio,'apad'])
    if any(clip.get(key) for key in ('logo_asset_id','filler_asset_id','music_asset_id','image_asset_id')) or clip.get('sound_effect','none')!='none':
        args+=compositor.build(directory,clip,assets or [],width,height,filters,post_filters,audio_filter,duration/speed,audio_index=audio_index)
    else:
        if post_filters:filters+=','+post_filters
        if clip.get('transition','none')!='none':
            fade=min(clip.get('transition_duration',.35),duration/speed/2)
            color='white' if clip['transition']=='white' else 'black'
            filters+=f',fade=t=in:st=0:d={fade}:color={color},fade=t=out:st={duration/speed-fade}:d={fade}:color={color}'
        args+=['-t',str(duration/speed),'-map','0:v:0','-sn','-dn','-vf',filters]
        args+=['-map',f'{audio_index}:a:0','-af',audio_filter] if audio_filter else ['-an']
    if clip.get('output_format','mp4') == 'webm':
        args += ['-c:v','libvpx-vp9','-deadline','realtime','-cpu-used','8','-row-mt','1','-crf','34','-b:v','0','-c:a','libopus']
    else:
        args += ['-c:v','libx264','-preset',{'fast':'ultrafast','standard':'veryfast','high':'fast'}[quality],'-crf',{'fast':'25','standard':'21','high':'19'}[quality],'-c:a','aac','-movflags','+faststart']
    args += ['-threads',str(max(1,min(4,(os.cpu_count() or 2)//2))),'-pix_fmt','yuv420p','-b:a','128k',str(output)]
    run(args, cwd=directory)
