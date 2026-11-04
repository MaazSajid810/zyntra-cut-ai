'use client';
import {useRef} from 'react';
export default function AudioCompare({projectId,clip}:{projectId:string;clip:{id:string;start:number;end:number;file:string|null}}){
  const original=useRef<HTMLAudioElement>(null),processed=useRef<HTMLAudioElement>(null);
  function pauseOthers(current:HTMLMediaElement){document.querySelectorAll('video,audio').forEach(media=>{if(media!==current)(media as HTMLMediaElement).pause();});}
  return <details className="audio-compare"><summary>Compare original and rendered audio</summary><p>Use headphones. Pause one track before playing the other. Voice effects change pitch/tone, not the speaker’s identity. Apply & render first to hear updated settings.</p><label>Original source audio<audio ref={original} aria-label="Original source audio" controls preload="none" src={`/api/projects/${projectId}/media/source#t=${clip.start},${clip.end}`} onPlay={e=>pauseOthers(e.currentTarget)} onLoadedMetadata={e=>{e.currentTarget.currentTime=clip.start;}} onTimeUpdate={e=>{if(e.currentTarget.currentTime>=clip.end)e.currentTarget.pause();}}/></label><label>Rendered clip audio<audio key={clip.file} ref={processed} aria-label="Rendered clip audio" controls preload="none" src={`/api/projects/${projectId}/media/${clip.id}?v=${encodeURIComponent(clip.file||'')}`} onPlay={e=>pauseOthers(e.currentTarget)}/></label></details>;
}
