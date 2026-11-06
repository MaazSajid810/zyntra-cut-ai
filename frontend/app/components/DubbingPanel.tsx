'use client';
import {useEffect,useState} from 'react';
import {platformApi} from '../../lib/platform';
import type {CaptionScript} from '../../lib/languages';

type Capabilities={installed:boolean;message:string;languages:{script:CaptionScript;language:string;name:string;available:boolean}[]};
export type DubbingState={enabled?:boolean;status?:string;language?:string;file?:string;video_file?:string;error?:string};
export default function DubbingPanel({projectId,language,current,disabled,error,onApply}:{projectId:string;language:string|null;current?:DubbingState;disabled:boolean;error?:string|null;onApply:(script:CaptionScript,enabled:boolean,render:boolean)=>Promise<void>}){
 const [capabilities,setCapabilities]=useState<Capabilities|null>(null),[failed,setFailed]=useState('');
 const [target,setTarget]=useState<CaptionScript>(language==='en'?'urdu':'english'),[render,setRender]=useState(true);
 useEffect(()=>{let active=true;setCapabilities(null);void platformApi<Capabilities>(`/projects/${projectId}/dubbing/capabilities`).then(value=>{if(active){setCapabilities(value);setFailed('');}}).catch(e=>{if(active)setFailed(e instanceof Error?e.message:'Could not read offline voice capabilities.');});return()=>{active=false;};},[projectId,language]);
 const choices=capabilities?.languages.filter(item=>item.available)||[];
 useEffect(()=>{if(choices.length&&!choices.some(item=>item.script===target))setTarget(choices[0].script);},[capabilities,target]);
 return <fieldset className="dubbing-panel"><legend>Translate captions + voice</legend>
  <p>Generate a basic offline synthetic voice in another language, fitted to each sentence’s time slot. Source video stays intact. Dubbing replaces original audio, including music and background sounds.</p>
  <p>Lips keep their original movements. This engine does not animate mouths or clone the speaker’s voice.</p>
  {failed&&<p role="alert">{failed}</p>}{error&&<p role="alert">Voice translation failed: {error}. Your previous captions and audio were kept.</p>}
  {current?.error&&<p role="status">{current.error}</p>}
  {capabilities&&!capabilities.installed&&<p role="status">Offline voices are not installed. Run the dubbing setup described in README, then reload.</p>}
  {capabilities?.installed&&!choices.length&&<p role="status">No installed voice and translation route match this source language. Re-transcribe the actual speech or install a supported translation model.</p>}
  <label>Voice translation language<select aria-label="Voice translation language" value={target} disabled={disabled||!choices.length} onChange={e=>setTarget(e.target.value as CaptionScript)}>{choices.map(item=><option key={item.script} value={item.script}>{item.name}</option>)}</select></label>
  <label className="check-field"><input type="checkbox" checked={render} disabled={disabled} onChange={e=>setRender(e.target.checked)}/>Render existing clips with the translated voice automatically</label>
  <div className="transcript-language-actions"><button type="button" className="primary" disabled={disabled||!choices.length} onClick={()=>void onApply(target,true,render)}>Translate captions + voice</button>
   {current?.enabled&&<button type="button" className="secondary" disabled={disabled} onClick={()=>void onApply(target,false,false)}>Use original audio</button>}
  </div>
  {current?.enabled&&current.status==='ready'&&<div><p role="status">Translated voice enabled ({current.language}). The video preview above and new clip exports use this track.</p>{current.video_file&&<a className="secondary" href={`/api/projects/${projectId}/dubbing/video?v=${encodeURIComponent(current.video_file)}`} download="zyntracut-translated.mp4">Download dubbed video</a>}<audio controls preload="none" src={`/api/projects/${projectId}/dubbing/audio?v=${encodeURIComponent(current.file||'')}`} aria-label="Translated voice preview"/></div>}
 </fieldset>;
}
