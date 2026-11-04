"""Single-encode FFmpeg layers: B-roll, logo, music and original synthesized SFX."""

SOUNDS={
    'pop':'aevalsrc=0.4*sin(2*PI*(150+900*exp(-30*t))*t)*exp(-35*t):d=0.18:s=48000',
    'ding':'sine=frequency=1320:duration=0.65:sample_rate=48000,afade=t=out:st=0.02:d=0.6',
    'whoosh':'anoisesrc=color=pink:duration=0.6:amplitude=0.25:seed=41,highpass=f=600,lowpass=f=6500,afade=t=in:d=0.1,afade=t=out:st=0.2:d=0.4',
}


def build(directory,clip,assets,width,height,filters,post_filters,audio_filter,length,audio_index=0):
    inputs=[];graph=[f'[0:v:0]{filters}[base]'];current='base';index=audio_index+1
    def asset(kind):
        nonlocal index
        key={'logo':'logo_asset_id','filler':'filler_asset_id','music':'music_asset_id','image':'image_asset_id'}[kind]
        asset_id=clip.get(key)
        if not asset_id:return None
        item=next((a for a in assets if a['id']==asset_id and a['kind']==kind),None)
        if not item:raise ValueError(f'The selected {kind} is unavailable in this project.')
        path=(directory/item['file']).resolve()
        if path.parent!=directory.resolve() or not path.is_file():raise ValueError('Uploaded asset file is unavailable.')
        n=index;index+=1
        inputs.extend(['-loop','1'] if kind in ('logo','image') else ['-stream_loop','-1'])
        inputs.extend(['-i',str(path)])
        return n
    filler=asset('filler')
    if filler:
        start=clip.get('filler_start',0);end=min(length,clip.get('filler_end',3));hold=end-start
        if hold<=0:raise ValueError('B-roll has no visible time inside this clip.')
        pip=clip.get('filler_layout','full')=='pip'
        w=max(2,int(width*(.38 if pip else 1)/2)*2);h=max(2,int(height*(.38 if pip else 1)/2)*2)
        layer=f'trim=duration={hold},setpts=PTS-STARTPTS,scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1,fps=30,format=rgba'
        if clip.get('transition')=='fade':
            fade=min(clip.get('transition_duration',.35),hold/2)
            layer+=f',fade=t=in:st=0:d={fade}:alpha=1,fade=t=out:st={hold-fade}:d={fade}:alpha=1'
        graph.append(f'[{filler}:v:0]{layer},setpts=PTS+{start}/TB[broll]')
        position='W-w-16:H-h-16' if pip else '0:0'
        graph.append(f"[{current}][broll]overlay={position}:eof_action=pass:repeatlast=0:enable='between(t,{start},{end})'[filled]")
        current='filled'
    photo=asset('image')
    if photo:
        start=clip.get('image_start',0);end=min(length,clip.get('image_end',3));hold=end-start
        if hold<=0:raise ValueError('Photo has no visible time inside this clip.')
        full=clip.get('image_layout','overlay')=='full'
        w=width if full else max(2,int(width*clip.get('image_width',35)/100/2)*2)
        h=height if full else max(2,int(height*.9/2)*2)
        if full and clip.get('image_fit','contain')=='cover':
            resize=f'scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}'
        else:
            resize=f'scale={w}:{h}:force_original_aspect_ratio=decrease'
            if full:resize+=f',pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black'
        layer=f'trim=duration={hold},setpts=PTS-STARTPTS,{resize},setsar=1,fps=30,format=rgba,colorchannelmixer=aa={clip.get("image_opacity",1)}'
        if clip.get('transition')=='fade':
            fade=min(clip.get('transition_duration',.35),hold/2)
            layer+=f',fade=t=in:st=0:d={fade}:alpha=1,fade=t=out:st={hold-fade}:d={fade}:alpha=1'
        graph.append(f'[{photo}:v:0]{layer},setpts=PTS+{start}/TB[photo]')
        position='0:0' if full else f'x=(W-w)*{clip.get("image_x",50)}/100:y=(H-h)*{clip.get("image_y",50)}/100'
        graph.append(f"[{current}][photo]overlay={position}:eof_action=pass:repeatlast=0:enable='between(t,{start},{end})'[pictured]")
        current='pictured'
    if post_filters:
        graph.append(f'[{current}]{post_filters}[captioned]');current='captioned'
    logo=asset('logo')
    if logo:
        w=max(2,int(width*clip.get('logo_width',18)/100/2)*2)
        graph.append(f'[{logo}:v:0]scale={w}:{max(2,int(height*.6/2)*2)}:force_original_aspect_ratio=decrease,format=rgba,colorchannelmixer=aa={clip.get("logo_opacity",.4)}[logo]')
        graph.append(f'[{current}][logo]overlay=x=(W-w)*{clip.get("logo_x",90)}/100:y=(H-h)*{clip.get("logo_y",10)}/100:shortest=0[branded]')
        current='branded'
    transition=clip.get('transition','none')
    if transition!='none':
        fade=min(clip.get('transition_duration',.35),length/2)
        color='white' if transition=='white' else 'black'
        graph.append(f'[{current}]fade=t=in:st=0:d={fade}:color={color},fade=t=out:st={length-fade}:d={fade}:color={color}[faded]')
        current='faded'
    graph.append(f'[{current}]format=yuv420p[outv]')
    tracks=[]
    if audio_filter:
        graph.append(f'[{audio_index}:a:0]{audio_filter}[voice]');tracks.append('voice')
    music=asset('music')
    if music:
        fade=min(.5,length/2)
        graph.append(f'[{music}:a:0]atrim=duration={length},asetpts=PTS-STARTPTS,aresample=48000,volume={clip.get("music_volume",.15)},afade=t=out:st={length-fade}:d={fade}[music]')
        tracks.append('music')
    sound=clip.get('sound_effect','none')
    if sound!='none':
        n=index;inputs.extend(['-f','lavfi','-i',SOUNDS[sound]])
        at=clip.get('sound_at',0)
        if at>=length:raise ValueError('Sound effect starts after this clip ends.')
        graph.append(f'[{n}:a:0]volume={clip.get("sound_volume",.5)},adelay={round(at*1000)}:all=1[sound]');tracks.append('sound')
    maps=['-map','[outv]']
    if tracks:
        graph.append(''.join(f'[{track}]' for track in tracks)+f'amix=inputs={len(tracks)}:duration=longest:normalize=0,alimiter=limit=0.95:level=disabled,apad[outa]')
        maps+=['-map','[outa]']
    else:maps+=['-an']
    return [*inputs,'-t',str(length),'-sn','-dn','-filter_complex_threads','1','-filter_complex',';'.join(graph),*maps]
