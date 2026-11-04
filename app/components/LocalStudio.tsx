'use client';
import Link from 'next/link';
import {useCallback,useEffect,useRef,useState} from 'react';
import {ArrowRight,Image as ImageIcon,LoaderCircle,Trash2,Video} from 'lucide-react';
import {platformApi,editorUrl} from '../../lib/platform';

type StudioJob={id:string;status:string;error:string|null;project_id:string|null;photo:boolean;created_at:string;options:{text:string;kind:'video'|'image';style:'bold'|'minimal'|'cinematic';duration:number;quality:string}};
export default function LocalStudio({refreshProjects}:{refreshProjects:()=>Promise<void>}){
 const [kind,setKind]=useState<'video'|'image'>('video'),[text,setText]=useState(''),[style,setStyle]=useState<'bold'|'minimal'|'cinematic'>('bold'),[duration,setDuration]=useState('8'),[quality,setQuality]=useState('480'),[file,setFile]=useState<File|null>(null),[jobs,setJobs]=useState<StudioJob[]>([]),[selected,setSelected]=useState(''),[pending,setPending]=useState(false),[error,setError]=useState(''),[loading,setLoading]=useState(true);
 const fileInput=useRef<HTMLInputElement>(null);
 const refresh=useCallback(async()=>{try{const value=await platformApi<StudioJob[]>('/studio');setJobs(value);setLoading(false);}catch(e){setError(e instanceof Error?e.message:'Could not load Studio.');}},[]);
 useEffect(()=>{void refresh();},[refresh]);
 const active=jobs.some(j=>['queued','rendering'].includes(j.status));
 useEffect(()=>{if(!active)return;const t=setInterval(()=>{void refresh();void refreshProjects();},1600);return()=>clearInterval(t);},[active,refresh,refreshProjects]);
 const job=jobs.find(j=>j.id===selected)||jobs.find(j=>j.status==='ready');
 async function create(){if(pending||active||!text.trim())return;setPending(true);setError('');try{
  const body=new FormData();body.append('text',text.trim());body.append('kind',kind);body.append('style',style);body.append('duration',duration);body.append('quality',quality);if(file)body.append('file',file);
  const item=await platformApi<StudioJob>('/studio',{method:'POST',body});setSelected(item.id);await refresh();
 }catch(e){setError(e instanceof Error?e.message:'Could not create this design.');}finally{setPending(false);}}
 async function remove(item:StudioJob){if(!window.confirm('Delete this Studio result and its associated video project, clips and files?'))return;setPending(true);setError('');
  const previous=Array.from(document.querySelectorAll('.studio-results video')).map(v=>({media:v as HTMLVideoElement,src:v.getAttribute('src')}));
  previous.forEach(({media})=>{media.pause();media.removeAttribute('src');media.load();});
  try{
  await platformApi('/studio/'+item.id,{method:'DELETE'});setSelected('');await refresh();await refreshProjects();
 }catch(e){previous.forEach(({media,src})=>{if(media.isConnected&&src){media.src=src;media.load();}});setError(e instanceof Error?e.message:'Could not delete this result.');}finally{setPending(false);}}
 return <section className="platform-studio"><div className="platform-page-heading"><div><h1>Studio</h1><p>Make a styled image or an animated vertical video, entirely on this computer.</p></div><span className="platform-local">Free · local rendering</span></div>
  <p className="platform-note">Create designs from your exact words and animate your own photos. Generating a new scene from a prompt needs a separate model and is not available in this local mode.</p>
  <div className="platform-pills" aria-label="Studio output"><button aria-pressed={kind==='video'} disabled={pending||active} onClick={()=>setKind('video')}><Video size={17}/>Video</button><button aria-pressed={kind==='image'} disabled={pending||active} onClick={()=>setKind('image')}><ImageIcon size={17}/>Image</button></div>
  <form className="studio-composer" onSubmit={e=>{e.preventDefault();void create();}}><div><label>Design style<select aria-label="Studio style" value={style} disabled={pending||active} onChange={e=>setStyle(e.target.value as typeof style)}><option value="bold">Modern bold</option><option value="minimal">Minimal light</option><option value="cinematic">Cinematic title</option></select></label><button className="platform-secondary" type="button" disabled={pending||active} onClick={()=>setText('One small idea.\nA whole new perspective.')}>Use an example title</button></div>
   <label className="studio-title-label">Your on-screen words<textarea aria-label="Studio title text" required maxLength={600} placeholder="Write the exact words you want on screen. This is a title design, not a scene-generation prompt." value={text} disabled={pending||active} onChange={e=>setText(e.target.value)}/></label>
   <div className="studio-photo"><label>Optional photo · PNG/JPEG/WebP · up to 20 MB<input ref={fileInput} aria-label="Studio photo" type="file" accept="image/png,image/jpeg,image/webp" disabled={pending||active} onChange={e=>{const f=e.target.files?.[0];if(f&&f.size>20*1024**2){setError('Photo exceeds the 20 MB limit.');e.target.value='';setFile(null);}else{setFile(f||null);setError('');}}}/></label>{file&&<button type="button" className="platform-secondary" onClick={()=>{setFile(null);if(fileInput.current)fileInput.current.value='';}}>Remove photo</button>}</div>
   <div className="studio-export-options">{kind==='video'&&<label>Duration<select aria-label="Studio duration" value={duration} disabled={pending||active} onChange={e=>setDuration(e.target.value)}>{[3,5,8,10,15].map(n=><option key={n} value={n}>{n} seconds</option>)}</select></label>}<label>Portrait size<select aria-label="Studio quality" value={quality} disabled={pending||active} onChange={e=>setQuality(e.target.value)}><option value="480">480px wide · Fast</option><option value="720">720 × 1280</option><option value="1080">1080 × 1920</option></select></label><button type="submit" disabled={pending||active||!text.trim()}>{pending||active?<LoaderCircle className="spin" size={18}/>:<ArrowRight size={18}/ >}{active?'Rendering locally…':`Create ${kind==='video'?'MP4':'PNG'}`}</button></div>
  </form>
  {error&&<p role="alert" className="platform-alert">{error}</p>}{active&&<p role="status" className="platform-note">Rendering a real file on your CPU. Download starts only when you choose it.</p>}
  <h2>Styles</h2><div className="studio-style-grid">{(['bold','minimal','cinematic'] as const).map(s=><button type="button" key={s} className={'studio-style '+s} aria-pressed={style===s} disabled={pending||active} onClick={()=>setStyle(s)}><span>YOUR WORDS.<br/>YOUR STORY.</span><strong>{s==='bold'?'Modern bold':s==='minimal'?'Minimal light':'Cinematic title'}</strong></button>)}</div>
  <section className="studio-results" aria-label="Studio results"><h2>Your creations</h2>{loading&&<p>Loading private results…</p>}{!loading&&!jobs.length&&<p>No creations yet. Write a title above to create your first real file.</p>}
   <div className="studio-history">{jobs.map(j=><article key={j.id}><button className="studio-job-select" aria-pressed={job?.id===j.id} onClick={()=>setSelected(j.id)}><strong>{j.options.text.slice(0,90)}</strong><small>{j.options.kind.toUpperCase()} · {j.status}</small></button><button aria-label={`Delete Studio result ${j.options.text.slice(0,90)}`} disabled={pending||['queued','rendering'].includes(j.status)} onClick={()=>void remove(j)}><Trash2 size={16}/></button>{j.error&&<p role="alert">{j.error}<button onClick={()=>{setText(j.options.text);setKind(j.options.kind);setStyle(j.options.style);setDuration(String(j.options.duration));setQuality(j.options.quality);}}>Reuse these settings</button></p>}</article>)}</div>
   {job?.status==='ready'&&<div className="studio-finished" role="region" aria-label="Finished Studio preview">{job.options.kind==='video'?<video key={job.id} src={`/api/studio/${job.id}/media`} controls playsInline preload="metadata"/>:<img src={`/api/studio/${job.id}/media`} alt={job.options.text}/>}<div><strong>{job.options.text}</strong><a href={`/api/studio/${job.id}/media`} download>Download {job.options.kind==='video'?'MP4':'PNG'} <ArrowRight size={16}/></a>{job.project_id&&<Link href={editorUrl(job.project_id)}>Open in full editor <ArrowRight size={16}/></Link>}</div></div>}
  </section>
 </section>;
}
