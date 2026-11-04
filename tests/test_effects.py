import json
import time
import subprocess

import av
import numpy as np
import pytest

from backend import main, media, store

@pytest.mark.parametrize('font',['Anton','Bebas Neue','Poppins','Righteous','Bangers','Lobster','Pacifico','Kalam'])
def test_bundled_font_is_selected_by_actual_libass(source,tmp_path,monkeypatch,font):
    logs=[]
    def verbose_run(args,cwd=None,timeout=1800):
        result=subprocess.run([media.FFMPEG,'-hide_banner','-loglevel','verbose','-y',*args],cwd=cwd,capture_output=True,text=True,timeout=timeout)
        assert result.returncode==0,result.stderr[-2000:]
        logs.append(result.stderr)
    monkeypatch.setattr(media,'run',verbose_run)
    output=tmp_path/'font.mp4'
    media.render(source,tmp_path,clip(subtitle_font=font,style='clean'),[{'start':0,'end':1.4,'text':'Real font selection'}],output)
    selected=[line.split('->',1)[1].replace(' ','').lower() for line in logs[0].splitlines() if 'fontselect:' in line and '->' in line]
    assert any(font.replace(' ','').lower() in line for line in selected),selected
    assert media.probe(output)['duration']==pytest.approx(1.5,abs=.15)


@pytest.fixture(scope='module')
def source(tmp_path_factory):
    path=tmp_path_factory.mktemp('effects')/'source.mp4'
    media.run(['-f','lavfi','-i','testsrc2=size=320x180:rate=15','-f','lavfi','-i','sine=frequency=440:sample_rate=48000','-t','2','-c:v','libx264','-c:a','aac',str(path)])
    return path


def clip(**changes):
    return {'id':'effect-test','start':0,'end':1.5,**main.EffectSettings().model_dump(),'aspect':'vertical','render_quality':'fast','sticker_enabled':'sticker' in changes,'voice_strength':.5,**changes}


def audio_frequency(path):
    with av.open(str(path)) as container:
        resampler=av.AudioResampler(format='fltp',layout='mono',rate=16000)
        chunks=[part.to_ndarray().reshape(-1) for frame in container.decode(audio=0) for part in resampler.resample(frame)]
    samples=np.concatenate(chunks)[3200:16000]
    spectrum=np.abs(np.fft.rfft(samples*np.hanning(len(samples))))
    return np.fft.rfftfreq(len(samples),1/16000)[spectrum.argmax()]


@pytest.mark.parametrize('sticker,position',[('subscribe','top-right'),('follow','bottom-left'),('like','top-left'),('subscribe','bottom-right')])
def test_stickers_are_burned_into_export_without_subtitles(source,tmp_path,sticker,position):
    output=tmp_path/'sticker.mp4'
    baseline=tmp_path/'plain.mp4'
    options=clip(style='none',aspect='square',speed=2,sticker=sticker,sticker_position=position)
    media.render(source,tmp_path,options,[],output)
    media.render(source,tmp_path,clip(style='none',aspect='square',speed=2),[],baseline)
    def pixels(path):
        with av.open(str(path)) as video:
            return list(video.decode(video=0))[-1].to_ndarray(format='rgb24').astype(float)
    difference=np.abs(pixels(output)-pixels(baseline)).mean(axis=2)
    # Padding is black in this square fixture: the sticker must change actual pixels
    # in its selected corner, even on the last frame after a speed change.
    corner=difference[:140] if position.startswith('top') else difference[-140:]
    corner=corner[:,:240] if position.endswith('left') else corner[:,240:]
    assert (corner>25).sum()>400
    ass=next(tmp_path.glob('*.ass')).read_text(encoding='utf-8')
    assert f',Sticker,,0,0,0,,{sticker.upper()}' in ass
    assert media.probe(output)['duration']==pytest.approx(.75,abs=.15)


@pytest.mark.parametrize('voice',['none','deep','high','radio','echo','mute'])
def test_real_voice_effects(source,tmp_path,voice):
    output=tmp_path/'voice.mp4'
    media.render(source,tmp_path,clip(voice_effect=voice,style='none'),[],output)
    info=media.probe(output)
    assert info['duration']==pytest.approx(1.5,abs=.15)
    assert info['has_audio']==(voice!='mute')
    if voice in ('none','deep','high'):
        assert audio_frequency(output)==pytest.approx({'none':440,'deep':352,'high':550}[voice],abs=10)


@pytest.mark.parametrize('effect',['none','vivid','warm','cool','mono','vintage','mirror'])
def test_real_video_effects(source,tmp_path,effect):
    output=tmp_path/'effect.mp4'
    media.render(source,tmp_path,clip(video_effect=effect,style='none',aspect='square'),[],output)
    with av.open(str(output)) as container:
        pixels=next(container.decode(video=0)).to_ndarray(format='rgb24')
    assert pixels.shape==(480,480,3)
    if effect=='mono':
        assert np.abs(pixels[:,:,0].astype(float)-pixels[:,:,1]).mean()<2
    if effect!='none':
        baseline=tmp_path/'baseline.mp4'
        media.render(source,tmp_path,clip(style='none',aspect='square'),[],baseline)
        with av.open(str(baseline)) as container:
            original=next(container.decode(video=0)).to_ndarray(format='rgb24')
        assert np.abs(pixels.astype(float)-original.astype(float)).mean()>1


@pytest.mark.parametrize('style,font',[('mint','Arial'),('clean','Arial'),('yellow','Impact'),('boxed','Georgia'),('neon','Arial'),('minimal','Arial'),('none','Arial')])
def test_subtitle_styles_custom_color_and_safe_overlay(source,tmp_path,style,font):
    output=tmp_path/'subtitles.mp4'
    options=clip(style=style,subtitle_font=font,subtitle_color='#123456',subtitle_position='top',subtitle_size=42,subtitle_uppercase=True,overlay_text='My hook {literal} \\ text',overlay_position='bottom')
    media.render(source,tmp_path,options,[{'start':.1,'end':1.2,'text':'Editable caption'}],output)
    ass=next(tmp_path.glob('*.ass')).read_text(encoding='utf-8')
    assert '&H00563412' in ass
    assert f'Default,{font},' in ass
    assert 'My hook (literal) ／ text' in ass
    assert ('EDITABLE CAPTION' in ass)==(style!='none')
    assert media.probe(output)['duration']==pytest.approx(1.5,abs=.15)


@pytest.mark.parametrize('aspect,expected',[('vertical',(480,854)),('square',(480,480)),('landscape',(854,480)),('portrait',(480,600)),('original',(320,180))])
def test_new_frame_formats(source,tmp_path,aspect,expected):
    output=tmp_path/'format.mp4'
    media.render(source,tmp_path,clip(aspect=aspect,style='none'),[],output)
    info=media.probe(output)
    assert (info['width'],info['height'])==expected


def test_webm_and_1080p(source,tmp_path):
    output=tmp_path/'export.webm'
    media.render(source,tmp_path,clip(output_format='webm',aspect='landscape',style='boxed',voice_effect='deep'),[{'start':0,'end':1,'text':'WebM subtitle'}],output)
    assert media.probe(output)['has_audio']
    with av.open(str(output)) as container:
        assert container.streams.video[0].codec_context.name=='vp9'
        assert container.streams.audio[0].codec_context.name=='opus'
    high=tmp_path/'high.mp4'
    media.render(source,tmp_path,clip(render_quality='high',style='none',end=.5),[],high)
    info=media.probe(high)
    assert (info['width'],info['height'])==(1080,1920)


def test_voice_effect_on_silent_video(tmp_path):
    source=tmp_path/'silent.mp4'
    media.run(['-f','lavfi','-i','color=c=black:s=160x90:r=15','-t','1','-c:v','libx264',str(source)])
    output=tmp_path/'silent-export.mp4'
    media.render(source,tmp_path,clip(voice_effect='deep',style='none',aspect='original',end=.8),[],output)
    assert not media.probe(output)['has_audio']


def test_subtitle_file_formats_and_relative_timing():
    segments=[{'start':5,'end':9,'text':'First caption'},{'start':9,'end':12,'text':'Second caption'}]
    srt=media.subtitle_file(segments,'srt',6,11)
    assert '00:00:00,000 --> 00:00:03,000' in srt
    assert '00:00:03,000 --> 00:00:05,000' in srt
    assert media.subtitle_file(segments,'vtt').startswith('WEBVTT\n\n1\n00:00:05.000')


@pytest.mark.parametrize('changes',[{'voice_effect':'invented'},{'video_effect':'arbitrary,filter'},{'subtitle_color':'{evil}'},{'subtitle_font':'bad,font'},{'subtitle_size':1000},{'output_format':'exe'},{'overlay_text':'x'*161}])
def test_invalid_effect_settings_are_rejected(changes):
    with pytest.raises(ValueError):
        main.EffectSettings(**changes)


@pytest.mark.parametrize('aspect',['vertical','square','landscape','portrait','original'])
def test_fit_preserves_both_source_edges(tmp_path,aspect):
    source=tmp_path/'edges.mp4'
    media.run(['-f','lavfi','-i','color=c=black:s=320x180:r=10',
               '-vf','drawbox=x=0:y=0:w=60:h=180:color=red:t=fill,drawbox=x=260:y=0:w=60:h=180:color=blue:t=fill',
               '-t','0.5','-c:v','libx264',str(source)])
    output=tmp_path/'fit.mp4'
    media.render(source,tmp_path,clip(aspect=aspect,style='none',end=.4),[],output)
    with av.open(str(output)) as container:
        pixels=next(container.decode(video=0)).to_ndarray(format='rgb24').astype(float)
    # Both edge markers must survive the actual encoded output in every ratio.
    assert ((pixels[:,:,0]>150)&(pixels[:,:,2]<80)).sum()>100
    assert ((pixels[:,:,2]>150)&(pixels[:,:,0]<80)).sum()>100


@pytest.mark.parametrize('axis,position,color',[('x',0,'red'),('x',100,'blue'),('y',0,'red'),('y',100,'blue')])
def test_manual_crop_position_moves_actual_output(tmp_path,axis,position,color):
    source=tmp_path/'position.mp4'
    size='320x180' if axis=='x' else '180x320'
    boxes=('drawbox=x=0:y=0:w=160:h=180:color=red:t=fill,drawbox=x=160:y=0:w=160:h=180:color=blue:t=fill'
           if axis=='x' else 'drawbox=x=0:y=0:w=180:h=160:color=red:t=fill,drawbox=x=0:y=160:w=180:h=160:color=blue:t=fill')
    media.run(['-f','lavfi','-i',f'color=c=black:s={size}:r=10','-vf',boxes,'-t','0.5','-c:v','libx264',str(source)])
    output=tmp_path/'crop.mp4'
    media.render(source,tmp_path,clip(framing='crop',aspect='vertical' if axis=='x' else 'landscape',style='none',end=.4,**{f'crop_{axis}':position}),[],output)
    with av.open(str(output)) as container:
        mean=next(container.decode(video=0)).to_ndarray(format='rgb24').mean(axis=(0,1))
    assert mean[0 if color=='red' else 2]>180
    assert mean[2 if color=='red' else 0]<60


@pytest.mark.parametrize('changes',[{'framing':'face-magic'},{'crop_x':-1},{'crop_x':101},{'crop_y':float('nan')}])
def test_invalid_framing_rejected(changes):
    with pytest.raises(ValueError):
        main.EffectSettings(**changes)


@pytest.mark.parametrize('aspect,framing,effect',[(a,'fit','none') for a in ['vertical','square','landscape','portrait','original']]+[('square','crop','none'),('original','fit','mirror')])
def test_webcam_cover_removes_region_before_reframing(tmp_path,aspect,framing,effect):
    source=tmp_path/'webcam.mp4'
    media.run(['-f','lavfi','-i','color=c=green:s=320x180:r=10',
               '-vf','drawbox=x=240:y=0:w=80:h=60:color=red:t=fill','-t','0.5','-c:v','libx264',str(source)])
    options=clip(aspect=aspect,framing=framing,crop_x=100,video_effect=effect,style='none',end=.4,
                 webcam_x=75,webcam_y=0,webcam_width=25,webcam_height=34)
    for hidden in [False,True]:
        output=tmp_path/f'cover-{hidden}.mp4'
        media.render(source,tmp_path,{**options,'hide_webcam':hidden},[],output)
        with av.open(str(output)) as container:
            pixels=next(container.decode(video=0)).to_ndarray(format='rgb24').astype(float)
        red=((pixels[:,:,0]>160)&(pixels[:,:,1]<70)&(pixels[:,:,2]<70)).sum()
        assert (red<20) if hidden else (red>100)
        assert ((pixels[:,:,1]>90)&(pixels[:,:,0]<60)).sum()>100


@pytest.mark.parametrize('changes',[{'webcam_x':-1},{'webcam_y':100},{'webcam_width':0},{'webcam_height':float('nan')},{'webcam_x':90,'webcam_width':20},{'webcam_y':90,'webcam_height':20}])
def test_invalid_webcam_bounds_rejected(changes):
    with pytest.raises(ValueError):
        main.EffectSettings(**changes)


@pytest.mark.parametrize('speed',[1,1.2,1.25,1.5,1.75,2,2.5,3,3.5,4])
def test_real_export_speed_audio_and_caption_sync(source,tmp_path,speed):
    output=tmp_path/'speed.mp4'
    options=clip(speed=speed,start=.3,end=1.8,aspect='original',style='cyan',overlay_text='Speed test')
    media.render(source,tmp_path,options,[{'start':.6,'end':1.4,'text':'Timed caption'}],output)
    info=media.probe(output)
    assert info['duration']==pytest.approx(1.5/speed,abs=.085)
    assert info['has_audio']
    assert audio_frequency(output)==pytest.approx(440,abs=12)
    ass=next(tmp_path.glob('*.ass')).read_text(encoding='utf-8')
    assert f'{media.stamp(.3/speed)},{media.stamp(1.1/speed)},Default' in ass
    assert f'{media.stamp(0)},{media.stamp(1.5/speed)},Overlay' in ass
    with av.open(str(output)) as container:
        frames=list(container.decode(video=0))
        assert float(frames[-1].pts*frames[-1].time_base)<1.5/speed+.05


@pytest.mark.parametrize('voice',['deep','high','mute'])
def test_speed_combines_with_voice_and_webm(source,tmp_path,voice):
    output=tmp_path/'speed.webm'
    media.render(source,tmp_path,clip(speed=2,voice_effect=voice,output_format='webm',aspect='original',style='none'),[],output)
    assert media.probe(output)['duration']==pytest.approx(.75,abs=.1)
    assert media.probe(output)['has_audio']==(voice!='mute')
    if voice!='mute':
        assert audio_frequency(output)==pytest.approx(352 if voice=='deep' else 550,abs=15)


@pytest.mark.parametrize('style',['cyan','orange','red','comic','elegant','shadow'])
def test_new_caption_designs_are_really_burned_in(source,tmp_path,style):
    output=tmp_path/'design.mp4'
    baseline=tmp_path/'baseline.mp4'
    media.render(source,tmp_path,clip(style=style,aspect='square'),[{'start':0,'end':1.5,'text':'New caption design'}],output)
    media.render(source,tmp_path,clip(style='none',aspect='square'),[],baseline)
    def pixels(path):
        with av.open(str(path)) as container:
            return next(container.decode(video=0)).to_ndarray(format='rgb24').astype(float)
    assert abs(pixels(output)-pixels(baseline)).sum()>10000


@pytest.mark.parametrize('speed',[0,.9,4.1,float('nan'),float('inf')])
def test_invalid_speed_rejected(speed):
    with pytest.raises(ValueError):
        main.EffectSettings(speed=speed)


def test_clip_subtitle_downloads_follow_speed(monkeypatch):
    project={'duration':20,'transcript':[{'start':6,'end':10,'text':'Speed caption'}],
             'clips':[{'id':'fast','start':5,'end':13,'speed':4}]}
    monkeypatch.setattr(main,'project_or_404',lambda _:project)
    for kind,separator in [('srt',','),('vtt','.')]:
        body=main.download_subtitles('project',kind,'fast').body.decode()
        assert f'00:00:00{separator}250 --> 00:00:01{separator}250' in body
    # Full-project downloads retain the original source timing.
    assert '00:00:06,000 --> 00:00:10,000' in main.download_subtitles('project','srt').body.decode()
