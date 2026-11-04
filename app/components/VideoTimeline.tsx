'use client';
type Cue={start:number;end:number;text:string};
export default function VideoTimeline({duration,current,segments,clip,onSeek}:{duration:number;current:number;segments:Cue[];clip?:{start:number;end:number;speed?:number;status:string};onSeek:(time:number)=>void}){
  const rendered=clip?.status==='ready';
  const start=clip?.start||0,end=clip?.end||duration,speed=rendered?(clip?.speed||1):1;
  const low=rendered?0:start,high=rendered?(end-start)/speed:end;
  const cues=segments.filter(s=>s.end>start&&s.start<end);
  return <section className="real-timeline" aria-label="Video and caption timeline"><label>Playhead ({current.toFixed(2)}s)<input aria-label="Timeline playhead" type="range" min={low} max={high} step="0.01" value={Math.max(low,Math.min(high,current))} onChange={e=>onSeek(Number(e.target.value))}/></label><p>Click a caption to seek. Trim boundaries are editable in the clip form below.</p><div className="caption-cue-track">{cues.slice(0,500).map((s,i)=><button type="button" title={s.text} aria-label={`Seek caption ${i+1}: ${s.text}`} key={i} onClick={()=>onSeek(rendered?(Math.max(start,s.start)-start)/speed:Math.max(start,s.start))}>{s.start.toFixed(1)}s · {s.text}</button>)}</div></section>;
}
