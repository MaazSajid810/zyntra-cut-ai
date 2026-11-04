'use client';
import {useRef,useState} from 'react';
import {Minus,Plus} from 'lucide-react';
import type {EffectSettings} from '../../lib/editor';

type Cue={start:number;end:number;text:string};
type Props={duration:number;start:number;end:number;current:number;effects:EffectSettings;segments:Cue[];waveform?:number[];waveformStep?:number;disabled:boolean;onGestureStart:()=>void;onGestureEnd:()=>void;onTrim:(start:number,end:number)=>void;onEffects:(patch:Partial<EffectSettings>)=>void;onSeek:(sourceSeconds:number)=>void};
const clamp=(v:number,a:number,b:number)=>Math.max(a,Math.min(b,v));
export default function VisualTimeline({duration,start,end,current,effects,segments,waveform=[],waveformStep=.5,disabled,onGestureStart,onGestureEnd,onTrim,onEffects,onSeek}:Props){
  const [zoom,setZoom]=useState(1);const canvas=useRef<HTMLDivElement>(null);
  const span=Math.max(.01,duration),length=(end-start)/effects.speed;
  const pos=(n:number)=>`${n/span*100}%`;
  function drag(event:React.PointerEvent,change:(delta:number)=>void){
    if(disabled)return;event.preventDefault();event.stopPropagation();onGestureStart();
    const element=event.currentTarget as HTMLElement;const origin=event.clientX;
    const width=canvas.current!.querySelector('.track-lane')!.getBoundingClientRect().width;element.setPointerCapture(event.pointerId);
    const move=(e:PointerEvent)=>change((e.clientX-origin)/width*span);
    const finish=()=>{onGestureEnd();element.removeEventListener('pointermove',move);element.removeEventListener('pointerup',finish);element.removeEventListener('pointercancel',finish);};
    element.addEventListener('pointermove',move);element.addEventListener('pointerup',finish);element.addEventListener('pointercancel',finish);
  }
  const trimStart=(value:number)=>onTrim(clamp(value,Math.max(0,end-600),end-.1),end);
  const trimEnd=(value:number)=>onTrim(start,clamp(value,start+.1,Math.min(duration,start+600)));
  function layer(label:string,kind:'image'|'filler'){
    const a=effects[`${kind}_start`],b=Math.min(length,effects[`${kind}_end`]);
    if(b<=a)return <div className="track-row"><span>{label}</span><small>Outside trimmed range; adjust timing in Media.</small></div>;
    const update=(x:number,y:number)=>onEffects({[`${kind}_start`]:Number(x.toFixed(3)),[`${kind}_end`]:Number(y.toFixed(3))});
    return <div className="track-row"><span>{label}</span><div className="track-lane"><div className="timeline-block layer-block" style={{left:pos(start+a*effects.speed),width:pos((b-a)*effects.speed)}}>
      <button disabled={disabled} type="button" aria-label={`Move ${label} on timeline`} onPointerDown={e=>drag(e,d=>{const next=clamp(a+d/effects.speed,0,length-(b-a));update(next,next+b-a);})} onKeyDown={e=>{if(!['ArrowLeft','ArrowRight'].includes(e.key))return;e.preventDefault();const next=clamp(a+(e.key==='ArrowLeft'?-.1:.1),0,length-(b-a));update(next,next+b-a);}}>{label}</button>
      <button disabled={disabled} type="button" className="trim-handle start" aria-label={`Trim ${label} start`} onPointerDown={e=>drag(e,d=>update(clamp(a+d/effects.speed,0,b-.1),b))} onKeyDown={e=>{if(['ArrowLeft','ArrowRight'].includes(e.key)){e.preventDefault();update(clamp(a+(e.key==='ArrowLeft'?-.1:.1),0,b-.1),b);}}}/>
      <button disabled={disabled} type="button" className="trim-handle end" aria-label={`Trim ${label} end`} onPointerDown={e=>drag(e,d=>update(a,clamp(b+d/effects.speed,a+.1,length)))} onKeyDown={e=>{if(['ArrowLeft','ArrowRight'].includes(e.key)){e.preventDefault();update(a,clamp(b+(e.key==='ArrowLeft'?-.1:.1),a+.1,length));}}}/>
    </div></div></div>;
  }
  return <section className="visual-timeline" aria-label="Editable clip timeline">
    <header><div><strong>Timeline</strong><small>Source seconds · drag the clip edges to trim</small></div><div className="timeline-zoom"><button type="button" aria-label="Zoom timeline out" disabled={zoom===1} onClick={()=>setZoom(z=>Math.max(1,z/2))}><Minus size={15}/></button><span>{zoom}×</span><button type="button" aria-label="Zoom timeline in" disabled={zoom===8} onClick={()=>setZoom(z=>Math.min(8,z*2))}><Plus size={15}/></button></div></header>
    <label className="timeline-scrub">Playhead ({current.toFixed(2)}s)<input aria-label="Timeline playhead" type="range" min={0} max={duration} step=".01" value={clamp(current,0,duration)} onChange={e=>onSeek(Number(e.target.value))}/></label>
    <div className="timeline-scroll"><div ref={canvas} className="timeline-canvas" style={{minWidth:zoom===1?'100%':`${zoom*100}%`}}>
      <div className="timeline-ruler">{Array.from({length:7},(_,i)=><span key={i}>{(duration*i/6).toFixed(1)}s</span>)}</div>
      <div className="track-row"><span>Video</span><div className="track-lane source-lane" onClick={e=>{const box=e.currentTarget.getBoundingClientRect();onSeek((e.clientX-box.left)/box.width*duration);}}><div className="timeline-block video-block" style={{left:pos(start),width:pos(end-start)}}>
        <button disabled={disabled} type="button" aria-label="Move video range" onPointerDown={e=>drag(e,d=>{const next=clamp(start+d,0,duration-(end-start));onTrim(next,next+end-start);})} onKeyDown={e=>{if(['ArrowLeft','ArrowRight'].includes(e.key)){e.preventDefault();const next=clamp(start+(e.key==='ArrowLeft'?-.1:.1),0,duration-(end-start));onTrim(next,next+end-start);}}}>Selected clip · {(end-start).toFixed(1)}s</button>
        <button disabled={disabled} type="button" role="slider" aria-label="Trim video start" aria-valuemin={Math.max(0,end-600)} aria-valuemax={end-.1} aria-valuenow={start} className="trim-handle start" onClick={e=>e.stopPropagation()} onPointerDown={e=>drag(e,d=>trimStart(start+d))} onKeyDown={e=>{if(['ArrowLeft','ArrowRight'].includes(e.key)){e.preventDefault();trimStart(start+(e.key==='ArrowLeft'?-.1:.1)*(e.shiftKey?10:1));}}}/>
        <button disabled={disabled} type="button" role="slider" aria-label="Trim video end" aria-valuemin={start+.1} aria-valuemax={Math.min(duration,start+600)} aria-valuenow={end} className="trim-handle end" onClick={e=>e.stopPropagation()} onPointerDown={e=>drag(e,d=>trimEnd(end+d))} onKeyDown={e=>{if(['ArrowLeft','ArrowRight'].includes(e.key)){e.preventDefault();trimEnd(end+(e.key==='ArrowLeft'?-.1:.1)*(e.shiftKey?10:1));}}}/>
      </div></div></div>
      <div className="track-row"><span>Captions</span><div className="track-lane caption-lane">{effects.style!=='none'?segments.map(s=>({...s,start:s.start+effects.caption_offset*effects.speed,end:s.end+effects.caption_offset*effects.speed})).filter(s=>s.end>start&&s.start<end).slice(0,500).map((s,i)=><button type="button" key={i} className="timeline-block caption-block" style={{left:pos(Math.max(start,s.start)),width:pos(Math.min(end,s.end)-Math.max(start,s.start))}} title={s.text} aria-label={`Seek caption ${i+1}: ${s.text}`} onClick={()=>onSeek(Math.max(start,s.start))}>{s.text}</button>):<small>Captions disabled for this clip</small>}</div></div>
      <div className="track-row"><span>Source audio</span><div className="track-lane waveform-lane">{waveform.length?<svg viewBox={`0 0 ${waveform.length} 32`} preserveAspectRatio="none" role="img" aria-label="Measured source audio waveform"><path d={waveform.map((v,i)=>`M${i},${16-Math.min(15,Math.sqrt(v)*30)}v${Math.min(30,Math.sqrt(v)*60)}`).join(' ')} stroke="currentColor" strokeWidth="1"/></svg>:<small>No measured waveform yet; Generate AI Clips analyzes the source.</small>}</div></div>
      {effects.image_asset_id&&layer('Photo','image')}{effects.filler_asset_id&&layer('B-roll','filler')}
      {effects.music_asset_id&&<div className="track-row"><span>Music</span><div className="track-lane"><div className="timeline-block music-block" style={{left:pos(start),width:pos(end-start)}}>Uploaded music · {Math.round(effects.music_volume*100)}%</div></div></div>}
      <div className="timeline-playhead" style={{left:`calc(86px + (100% - 86px) * ${clamp(current/span,0,1)})`}}/>
    </div></div>
    <p>Video trim uses source time. Photo/B-roll moves and trims update their saved output timing. {waveform.length?`Waveform measured every ${waveformStep.toFixed(1)}s.`:''} Save or Apply & render to commit edits.</p>
  </section>;
}
