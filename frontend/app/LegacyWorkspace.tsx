'use client';

import {useCallback, useEffect, useRef, useState} from 'react';
import {decodeApiResponse,ensureGuestSession,guestFetch} from '../lib/api';
import {type Clip,type EffectSettings,defaultEffects,subtitleStyles} from '../lib/editor';
import {recognitionChoices,type TranscriptionMode} from '../lib/speech';
import AudioCompare from './components/AudioCompare';
import ClipReview from './components/ClipReview';
import ClipDuration,{validDuration} from './components/ClipDuration';
import ProcessingNotice,{ProcessingReopen} from './components/ProcessingNotice';
import ClipForm from './components/ClipForm';
import ClipLibrary from './components/ClipLibrary';
import StudioHero from './components/StudioHero';
import {BRAND} from '../lib/brand';
import SubtitleOptions,{CaptionScript,SpeechLanguage} from './components/SubtitleOptions';
import TranscriptLanguageControls from './components/TranscriptLanguageControls';
import DubbingPanel,{type DubbingState} from './components/DubbingPanel';
import VideoTimeline from './components/VideoTimeline';
import LinkImporter from './components/LinkImporter';
import UsageGuide from './components/UsageGuide';
import GuestPrivacy from './components/GuestPrivacy';
import {ArrowDownToLine, ArrowLeft, ArrowRight, AudioLines, Check, ChevronRight, Clapperboard, Clock3, FileVideo, Film, FolderOpen, LayoutDashboard, LoaderCircle, MonitorPlay, Plus, Search, Settings2, ShieldCheck, Sparkles, UploadCloud, WandSparkles, X, Link2, Trash2, PanelLeftClose, PanelLeftOpen} from 'lucide-react';

type Segment = {id:number; start:number; end:number; text:string; source_text?:string; translation_warning?:string};
export type Project = {id:string; name:string; duration:number; size:number; created_at:string; status:string; error:string|null; language:string|null; processing_message?:string|null; caption_script?:CaptionScript; speech_language?:SpeechLanguage; has_audio?:boolean;auto_count?:boolean;min_duration?:number;max_duration?:number;media_analysis?:{waveform:number[];waveform_step:number};analysis_error?:string|null;caption_warning?:string|null;speech_warning?:string|null;dubbing?:DubbingState;dubbing_error?:string|null;source_transcript?:Segment[];default_effects?:Partial<EffectSettings>;transcript:Segment[]; clips:Clip[]; requested_clip_count?:number; transcription_mode?:TranscriptionMode; transcription_progress?:number; selection_mode?:'quality'|'all'; minimum_score?:number; clip_generation?:{requested:number;created:number;message:string;batch_id:string;empty_reason?:string|null;shortfall_message?:string|null;diagnostics?:{candidate_ranges:number;below_score:number;passed_score:number;overlap_existing:number;overlap_selected:number;duplicate_existing:number;duplicate_selected:number;selected:number;search_exhausted:boolean}}};
const time = (s:number) => `${Math.floor(s/60)}:${Math.floor(s%60).toString().padStart(2,'0')}`;
const busy = (s:string) => ['queued','transcribing','analyzing','rendering'].includes(s);
function releasePreviewMedia(){const previous=Array.from(document.querySelectorAll('video,audio')).map(element=>({media:element as HTMLMediaElement,src:element.getAttribute('src')}));previous.forEach(({media})=>{media.pause();media.removeAttribute('src');media.load();});return ()=>previous.forEach(({media,src})=>{if(media.isConnected&&src&&!media.getAttribute('src')){media.src=src;media.load();}});}
const media = (id:string, kind:string, version?:string|null) => `/api/projects/${id}/media/${kind}`+(version?'?v='+encodeURIComponent(version):'');
async function api<T>(path:string, options?:RequestInit):Promise<T> {
  const response = await guestFetch(`/api${path}`,options);
  return decodeApiResponse<T>(await response.text(), response.status);
}

export default function LegacyWorkspace({initialProjectId=null,initialClipId=null}:{initialProjectId?:string|null;initialClipId?:string|null}) {
  const [compact,setCompact]=useState(false);
  const [projects,setProjects] = useState<Project[]>([]);
  const [selected,setSelected] = useState<string|null>(initialProjectId);
  const [selectedClip,setSelectedClip]=useState<string|null>(initialClipId);
  const [view,setView] = useState('Overview');
  const [query,setQuery] = useState('');
  const [online,setOnline] = useState(false);
  const [loaded,setLoaded] = useState(false);
  const [notice,setNotice] = useState('');
  const [deletingId,setDeletingId]=useState<string|null>(null);
  const [uploading,setUploading] = useState(false);
  const [progress,setProgress] = useState(0);
  const [drag,setDrag] = useState(false);
  const [help,setHelp] = useState(false);
  const picker = useRef<HTMLInputElement>(null);
  const refreshSequence=useRef(0);
  const refresh = useCallback(async()=>{
    const sequence=++refreshSequence.current;
    try { const data = await api<Project[]>('/projects'); if(sequence===refreshSequence.current){setProjects(data);setOnline(true);} }
    catch {if(sequence===refreshSequence.current)setOnline(false);} finally {setLoaded(true);}
  },[]);
  useEffect(()=>{void refresh(); const timer = setInterval(()=>void refresh(),2500); return ()=>clearInterval(timer);},[refresh]);
  const project = projects.find(p=>p.id===selected);
  const totalClips = projects.flatMap(p=>p.clips);
  const exports = totalClips.filter(c=>c.status==='ready');
  async function upload(file?:File) {
    if(!file || uploading) return;
    if(file.size>2*1024**3) {setNotice('Choose a video smaller than 2 GB.');return;}
    setUploading(true); setProgress(0);setNotice('');
    try{await ensureGuestSession();}catch(e){setUploading(false);setNotice(e instanceof Error?e.message:'Could not start a private session.');return;}
    const xhr = new XMLHttpRequest(); xhr.open('POST','/api/projects');
    xhr.upload.onprogress = e=>{if(e.lengthComputable)setProgress(Math.round(e.loaded/e.total*100));};
    xhr.onload = ()=>{setUploading(false); try {const result = decodeApiResponse<Project>(xhr.responseText,xhr.status);setProjects(prev=>[result,...prev.filter(p=>p.id!==result.id)]);setSelected(result.id);setOnline(true);} catch(e) {setNotice(e instanceof Error?e.message:'Upload failed');}};
    xhr.onerror = ()=>{setUploading(false);setNotice('Upload could not reach the backend. Check the server and try again.');};
    const form = new FormData();form.append('file',file);xhr.send(form);
  }
  async function deleteProject(p:Project){
    if(deletingId||busy(p.status)||p.clips.some(c=>busy(c.status)))return;
    if(!window.confirm(`Delete "${p.name}" and all its source video, subtitles and clips? This cannot be undone.`))return;
    const restorePreview=releasePreviewMedia();setDeletingId(p.id);
    try{
      await api(`/projects/${p.id}`,{method:'DELETE'});
      ++refreshSequence.current;
      setProjects(prev=>prev.filter(item=>item.id!==p.id));
      if(selected===p.id)setSelected(null);
      setNotice('Project and its files deleted.');
      await refresh();
    }catch(error){restorePreview();setNotice(error instanceof Error?error.message:'Could not delete project.');}
    finally{setDeletingId(null);}
  }
  function navigate(name:string) {setView(name);setSelected(null);setSelectedClip(null);setQuery('');}
  return <div className={`shell ${compact?'compact':''}`}>
    <input ref={picker} type="file" accept="video/*,.mkv,.mov,.webm" hidden onChange={e=>{upload(e.target.files?.[0]);e.target.value='';}}/>
    <aside className="sidebar">
      <a href="/" className="brand"><span className="brand-mark"><Clapperboard size={22}/></span>{BRAND}<span className="ai-tag">AI</span></a>
      <div className="workspace"><span className="avatar">C</span><div>Creator workspace<small>Local workspace</small></div><ShieldCheck size={16}/></div>
      <div className="nav-label">WORKSPACE</div>
      <nav>{[{name:'Overview',icon:LayoutDashboard},{name:'Link to clips',icon:Link2},{name:'My projects',icon:FolderOpen},{name:'All clips',icon:Film},{name:'Exports',icon:ArrowDownToLine}].map(({name,icon:Icon})=><button key={name} className={view===name?'nav-item active':'nav-item'} onClick={()=>navigate(name)}><Icon size={18}/>{name}{name==='My projects'&&<span className="nav-count">{projects.length}</span>}</button>)}</nav>
      <div className="nav-label tools-label">STUDIO</div>
      <button className="nav-item" onClick={()=>picker.current?.click()}><WandSparkles size={18}/>Create clips<Plus size={15} className="push"/></button>
      <button className="nav-item" onClick={()=>setHelp(true)}><Settings2 size={18}/>Setup & workflow</button>
      <div className="local-card"><div className="local-icon"><ShieldCheck size={20}/></div><strong>Your content. Your machine.</strong><p>No credits, no watermark.<br/>Create with open-source tools.</p><span><span className="dot"/> Local processing</span></div>
      <button className="sidebar-toggle" type="button" aria-label={compact?'Expand sidebar':'Collapse sidebar'} aria-expanded={!compact} onClick={()=>setCompact(value=>!value)}>{compact?<PanelLeftOpen size={17}/>:<PanelLeftClose size={17}/>}Collapse sidebar</button>
      <div className="sidebar-bottom"><span className={`dot ${online?'':'offline'}`}/>{online?'Backend connected':'Backend offline'}<span className="version">v0.1</span></div>
    </aside>
    <main>
      <header className="topbar"><div className="breadcrumb">Workspace<ChevronRight size={14}/><span>{project?'Video editor':view}</span></div><div className="top-actions"><span className="local-pill"><ShieldCheck size={14}/>Private guest workspace</span><button className="profile" onClick={()=>setHelp(true)} aria-label="Workspace information">C</button></div></header>
      <div className="content">
        {notice&&<div className="alert" role="alert">{notice}<button onClick={()=>setNotice('')} aria-label="Dismiss message"><X size={16}/></button></div>}
        {loaded&&!online&&<div className="connection"><span className="dot offline"/><span>Start the Python backend to upload and process videos.</span><button onClick={()=>setHelp(true)}>Setup instructions <ArrowRight size={14}/></button></div>}
        {project ? <Editor key={project.id} project={project} initialClipId={selectedClip} onBack={()=>{setSelected(null);setSelectedClip(null);}} refresh={refresh} notify={setNotice}/> : <>
          <div className="page-heading"><div><div className="eyebrow">YOUR CREATIVE SPACE</div><h1>{view==='Overview'?'A little footage. Endless possibilities.':view}</h1><p>{view==='Overview'?'Turn your long-form videos into your next great short.':'Everything you create, all in one place.'}</p></div><button className="primary" onClick={()=>picker.current?.click()} disabled={uploading}><Plus size={17}/>New project</button></div>
          {view==='Overview'&&<>
            <section className="hero"><div className="hero-copy"><span className="hero-label"><Sparkles size={14}/> LESS EDITING. MORE CREATING.</span><h2>Your next standout clip<br/>is already in your video.</h2><p>Find the good parts. Add your style.<br/>Make something worth watching.</p><button className="primary" onClick={()=>picker.current?.click()} disabled={uploading}>Create your first {projects.length?'new clip':'clips'}<ArrowRight size={17}/></button><div className="hero-foot"><Check size={13}/>No watermark<span>·</span><Check size={13}/>100% yours</div></div><div className="hero-art" aria-hidden="true"><div className="orbit orbit-one"/><div className="orbit orbit-two"/><div className="float-label"><AudioLines size={17}/>Find your moment</div><div className="art-video back"><div className="abstract-light"/><span>LONG STORY</span></div><div className="art-video front"><div className="abstract-light"/><div className="play-disc"><MonitorPlay size={26}/></div><div className="art-subtitle">MAKE IT<br/><em>UNMISSABLE.</em></div><div className="art-timeline">▂ ▅ ▃ ▆ ▄ ▇ ▃ ▅ ▂ ▄ ▆ ▃</div></div><span className="art-badge"><Sparkles size={14}/> Made for the moment</span></div></section>
            <div className="stats-grid">{[{label:'Your projects',value:projects.length,icon:FolderOpen,sub:'A home for every idea'},{label:'Clips created',value:totalClips.length,icon:Film,sub:'Good moments, ready to shape'},{label:'Minutes uploaded',value:Math.round(projects.reduce((a,p)=>a+p.duration,0)/60),icon:Clock3,sub:'More stories to discover'},{label:'Video exports',value:exports.length,icon:ArrowDownToLine,sub:'Ready for the world'}].map(({label,value,icon:Icon,sub})=><div className="stat" key={label}><div className="stat-top">{label}<Icon size={17}/></div><strong>{value.toString().padStart(2,'0')}</strong><small>{sub}</small></div>)}</div>
            <section className={`upload-zone ${drag?'dragging':''}`} onDragOver={e=>{e.preventDefault();setDrag(true);}} onDragLeave={()=>setDrag(false)} onDrop={e=>{e.preventDefault();setDrag(false);upload(e.dataTransfer.files[0]);}}><div className="upload-symbol">{uploading?<LoaderCircle className="spin" size={23}/>:<UploadCloud size={25}/>}</div><div><h3>{uploading?progress===100?'Validating video & creating preview…':`Uploading your video… ${progress}%`:'Start with a video. We’ll find the possibilities.'}</h3><p>Drop a video here, or choose a file · MP4, MOV, WebM, MKV · Up to 2 GB</p></div><button className="secondary" onClick={()=>picker.current?.click()} disabled={uploading}><Plus size={16}/>Upload video</button>{uploading&&<progress value={progress} max={100}/>}</section>
          </>}
          {view==='Overview'&&<UsageGuide/>}
          {view==='Overview'&&<LinkImporter onUpload={()=>picker.current?.click()} onProject={async id=>{await refresh();setSelected(id);}}/>}
          {view==='Link to clips'&&<StudioHero/>}
          {view==='Link to clips'&&<LinkImporter studio onUpload={()=>picker.current?.click()} onProject={async id=>{await refresh();setSelected(id);}}/>}
          {view!=='Link to clips'&&<section className="library"><div className="section-heading"><div><h2>{view==='Overview'?'Recent projects':view}</h2><p>{view==='Exports'?'Rendered videos, ready to download.':'Pick up where your creativity left off.'}</p></div><label className="search"><Search size={16}/><input aria-label="Search projects" placeholder="Search projects…" value={query} onChange={e=>setQuery(e.target.value)}/></label></div>
            {(view==='Overview'||view==='My projects') ? <div className="projects-grid">{projects.filter(p=>p.name.toLowerCase().includes(query.toLowerCase())).map(p=><article className="project-entry" key={p.id}><button className="project-card" onClick={()=>setSelected(p.id)}><div className="project-image" style={{backgroundImage:`url("${media(p.id,'poster')}")`}}><span className="duration">{time(p.duration)}</span><span className={`status ${p.status==='error'?'error':''}`}>{busy(p.status)&&<LoaderCircle size={12} className="spin"/>}{p.status}</span></div><div className="project-details"><h3>{p.name}</h3><p>{p.clips.length} clips<span>·</span>{new Date(p.created_at).toLocaleDateString(undefined,{month:'short',day:'numeric'})}<ArrowRight size={15}/></p></div></button><div className="project-entry-actions"><button className="project-delete-button" type="button" aria-label={`Delete project ${p.name}`} disabled={!!deletingId||busy(p.status)||p.clips.some(c=>busy(c.status))} onClick={()=>void deleteProject(p)}>{deletingId===p.id?<LoaderCircle size={15} className="spin"/>:<Trash2 size={15}/>}Delete project</button>{(busy(p.status)||p.clips.some(c=>busy(c.status)))&&<small>Available after processing finishes</small>}</div></article>)}</div> : <ClipLibrary projects={projects} query={query} exportsOnly={view==='Exports'} onOpen={(projectId,clipId)=>{setSelectedClip(clipId);setSelected(projectId);}} onDeleted={refresh}/>}
            {!(view==='Exports'?exports.length:view==='All clips'?totalClips.length:projects.length)&&<div className="empty"><div className="empty-icon"><FileVideo size={27}/></div><h3>{view==='Exports'?'Your next export starts here':view==='All clips'?'Make room for great moments':'Your story starts here'}</h3><p>{view==='Exports'?'Render a clip in the editor to see your video exports here.':'Upload your first video and turn a long story into something short.'}</p><button className="text-button" onClick={()=>picker.current?.click()}>Upload a video<ArrowRight size={15}/></button></div>}
            {(view==='Overview'||view==='My projects')&&projects.length>0&&query&&!projects.some(p=>(p.name+' '+p.clips.map(c=>c.title).join(' ')).toLowerCase().includes(query.toLowerCase()))&&<p className="muted">No matches. Try a different search.</p>}
          </section>}<footer><span>Built for your creative flow.</span><span>Local-first. Open source. Always your content.</span></footer>
        </>}
      </div>
    </main>
    {help&&<div className="modal-backdrop" onClick={()=>setHelp(false)}><section className="modal" role="dialog" aria-modal="true" aria-label="Setup and workflow" onClick={e=>e.stopPropagation()}><button className="modal-close" onClick={()=>setHelp(false)} aria-label="Close instructions"><X/></button><UsageGuide/><GuestPrivacy onRestore={refresh}/><button className="primary" onClick={()=>setHelp(false)}>Got it<Check size={16}/></button></section></div>}
  </div>;
}

function Editor({project:p,initialClipId,onBack,refresh,notify}:{project:Project;initialClipId?:string|null;onBack:()=>void;refresh:()=>Promise<void>;notify:(text:string)=>void}) {
  const [segments,setSegments] = useState(p.transcript);
  const [dirty,setDirty] = useState(false);
  const [pending,setPending] = useState(false);
  const [generationPending,setGenerationPending]=useState(false);
  const [clipId,setClipId] = useState<string|null>(()=>p.clips.some(clip=>clip.id===initialClipId)?initialClipId??null:null);
  const [tab,setTab] = useState('Clips');
  const [originalPreview,setOriginalPreview]=useState(false);
  const dubbedPreview=!originalPreview&&p.dubbing?.enabled&&p.dubbing.status==='ready'&&!!p.dubbing.video_file;
  const [reviewId,setReviewId]=useState<string|null>(null);
  const [playhead,setPlayhead] = useState(0);
  const player = useRef<HTMLVideoElement>(null);
  const [progressVisible,setProgressVisible]=useState(true);
  const [aiOpen,setAiOpen]=useState(!p.clips.length);
  const clip = p.clips.find(c=>c.id===clipId);

  useEffect(()=>{if(!dirty)setSegments(p.transcript);},[p.transcript,dirty]);
  async function action(path:string,body?:unknown,method='POST',onSuccess?:()=>void) {setPending(true);try {await api(path,{method,headers:body?{'Content-Type':'application/json'}:undefined,body:body?JSON.stringify(body):undefined});await refresh();onSuccess?.();}catch(e){notify(e instanceof Error?e.message:'Request failed');}finally{setPending(false);}}
  const processing = busy(p.status)||p.clips.some(c=>busy(c.status));
  const reviewedBatch=useRef(p.clip_generation?.batch_id);
  useEffect(()=>{
    const batch=p.clip_generation;
    if(batch?.created&&!generationPending&&batch.batch_id!==reviewedBatch.current){reviewedBatch.current=batch.batch_id;setAiOpen(false);setClipId(null);setReviewId(null);}
  },[p.clip_generation,processing,generationPending]);
  const reviewing=tab==='Clips'&&!clip&&p.clips.length>0;
  const reviewClip=p.clips.find(c=>c.id===reviewId)||p.clips.find(c=>c.status==='ready')||p.clips[0];
  const subtitle = segments.find(s=>playhead>=s.start&&playhead<s.end);
  useEffect(()=>{if(processing)setProgressVisible(true);},[processing]);
  async function generateClips(count:number,mode:string,selection:'quality'|'all',threshold:number,autoRender:boolean,look:EffectSettings,captionScript:CaptionScript,speechLanguage:SpeechLanguage,minDuration:number,maxDuration:number):Promise<Project>{
    setPending(true);setGenerationPending(true);setProgressVisible(true);
    try{
      const result=await api<Project>(`/projects/${p.id}/${p.transcript.length?'highlights':'transcribe'}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({clip_count:count||100,auto_count:count===0,min_duration:minDuration,max_duration:maxDuration,transcription_mode:mode,caption_script:captionScript,speech_language:speechLanguage,selection_mode:selection,minimum_score:threshold,auto_render:autoRender,background:true,generated_settings:look})});
      await refresh();setTab('Clips');return result;
    }finally{setPending(false);setGenerationPending(false);}
  }
  async function applyAll(settings:unknown,includeReady=false){
    setPending(true);
    try{
      await api(`/projects/${p.id}/clips/settings${includeReady?'?include_ready=true':''}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(settings)});
      if(includeReady)await api(`/projects/${p.id}/clips/render`,{method:'POST'});
      notify(includeReady?'Ratio, captions, effects, audio and branding saved for every clip. Rendering updated exports…':'Current styling and export settings saved for drafts. Render all drafts to update the videos.');
    }catch(error){notify(error instanceof Error?error.message:'Could not update clips.');}
    finally{try{await refresh();}finally{setPending(false);}}
  }
  async function saveAndRender(id:string,body:unknown){
    setPending(true);
    try{
      await api(`/projects/${p.id}/clips/${id}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
      await api(`/projects/${p.id}/clips/${id}/render`,{method:'POST'});
      notify('Changes saved. Rendering your updated filter, fonts and effects…');
    }catch(error){notify(error instanceof Error?error.message:'Could not apply and render changes.');}
    finally{await refresh();setPending(false);}
  }
  async function deleteSelectedClips(ids:string[]){
    if(pending||processing||!ids.length||!window.confirm(`Delete ${ids.length} selected clips and their exports? The source video stays.`))return false;
    const restorePreview=releasePreviewMedia();setPending(true);const failed:string[]=[];
    try{for(const id of ids){try{await api(`/projects/${p.id}/clips/${id}`,{method:'DELETE'});}catch(e){failed.push(e instanceof Error?e.message:'Deletion failed.');}}}
    finally{try{await refresh();}finally{requestAnimationFrame(restorePreview);setPending(false);}if(failed.length)notify(`${failed.length} clips could not be deleted: ${failed.join('; ')}`);}
    return failed.length===0;
  }
  return <>
    {(processing||generationPending)&&progressVisible&&<ProcessingNotice title={generationPending?'Preparing automatic clips':p.status==='transcribing'?'Transcribing audio':p.status==='analyzing'?'Finding highlight moments':p.status==='queued'?'Your video is queued':'Rendering clip previews'} message={generationPending?'Submitting your automatic generation request…':busy(p.status)?(p.processing_message||'Captions and clips are being generated automatically. You do not need to create them manually.'):'Preparing playable previews with your selected captions and effects.'} progress={p.status==='transcribing'?p.transcription_progress:null} details={!busy(p.status)&&!generationPending&&p.clips.length?`${p.clips.filter(c=>c.status==='ready').length} / ${p.clips.length} previews ready`:undefined} onDismiss={()=>setProgressVisible(false)}/>}
    {(processing||generationPending)&&!progressVisible&&<ProcessingReopen onShow={()=>setProgressVisible(true)}/>}
    <div className="editor-navigation"><button className="text-button back-button" onClick={onBack}><ArrowLeft size={16}/>Back to workspace</button><div className="editor-project-delete"><button className="project-delete-button" disabled={processing||pending} onClick={async()=>{if(!window.confirm('Delete this project and all its source video, subtitles, and exports?'))return;const restorePreview=releasePreviewMedia();setPending(true);try{await api(`/projects/${p.id}`,{method:'DELETE'});await refresh();onBack();}catch(e){restorePreview();notify(e instanceof Error?e.message:'Delete failed');}finally{setPending(false);}}}><Trash2 size={15}/>Delete project</button></div></div>
    <div className="page-heading editor-heading"><div><div className="eyebrow">THE EDITING ROOM</div><h1>{p.name}</h1><p>{time(p.duration)} · {(p.size/1024**2).toFixed(1)} MB · {p.language?`Detected language: ${p.language}`:'Your original footage'}</p></div><span className="status standalone">{busy(p.status)&&<LoaderCircle className="spin" size={14}/>} {p.status}</span></div>
    <nav className="clip-workflow" aria-label="Clipping workflow">
      <button type="button" onClick={onBack}><span>1</span>Import video</button>
      <button type="button" aria-current={!p.clips.length?'step':undefined} onClick={()=>{setAiOpen(true);setClipId(null);setTab('Clips');}}><span>2</span>{processing?'Processing':'AI analysis'}</button>
      <button type="button" disabled={!p.clips.length} aria-current={reviewing?'step':undefined} onClick={()=>{setClipId(null);setTab('Clips');setAiOpen(false);}}><span>3</span>Review clips</button>
      <button type="button" disabled={!clip} aria-current={clip?'step':undefined} onClick={()=>setTab('Clips')}><span>4</span>Edit & export</button>
    </nav>
    {clip&&tab==='Clips'&&<button type="button" className="secondary results-back" onClick={()=>{setClipId(null);setAiOpen(false);}}><ArrowLeft size={15}/>Back to clip previews</button>}
    {p.error&&<div className="alert" role="alert">{p.error}</div>}{p.analysis_error&&<p className="filter-hint" role="status">{p.analysis_error}</p>}
    {p.caption_warning&&<p className="filter-hint" role="status">{p.caption_warning}</p>}
    {p.speech_warning&&<p className="filter-hint" role="status">{p.speech_warning}</p>}
    {p.transcript.length>0&&<button type="button" className="secondary" disabled={pending||processing||dirty} onClick={()=>{setTab('Transcript');void action(`/projects/${p.id}/transcribe`,{redo:true,transcription_mode:'quick',caption_script:p.caption_script||'original',speech_language:'auto'});}}>Detect & repair captions</button>}
    {p.transcript.length>0&&<button type="button" className="primary" disabled={pending||processing||dirty} onClick={()=>{setClipId(null);setTab('Transcript');requestAnimationFrame(()=>document.querySelector('.dubbing-panel')?.scrollIntoView({behavior:'smooth',block:'center'}));}}>Translate captions + voice</button>}
    {segments.some(s=>s.translation_warning)&&<div className="alert" role="alert">A translated sentence needs a meaning check. <button type="button" className="text-button" onClick={()=>setTab('Transcript')}>Review translation against original speech text</button></div>}
    {p.transcript.length>0&&<div className="subtitle-downloads"><a className="secondary" href={`/api/projects/${p.id}/subtitles?format=srt`} download><ArrowDownToLine size={14}/>Download saved SRT</a><a className="secondary" href={`/api/projects/${p.id}/subtitles?format=vtt`} download><ArrowDownToLine size={14}/>Download saved VTT</a></div>}
    <div className={`creator-editor ${clip&&tab==='Clips'?'editing':reviewing?'reviewing':''}`}><div className="editor-grid">{(tab==='Transcript'||(!clip&&tab!=='New clip'))&&<section className="preview-panel"><div className="panel-heading"><h3><MonitorPlay size={17}/>{clip?.status==='ready'?'Rendered clip preview':clip?'Source range preview':dubbedPreview?'Dubbed video preview':'Source preview'}</h3><span>{clip?.status==='ready'?clip.aspect:'Original'}</span></div><div className="video-stage"><video key={clip?clip.id+(clip.file||'source'):p.id+(dubbedPreview?p.dubbing?.video_file:'source')} ref={player} controls preload="metadata" onPlay={()=>document.querySelectorAll('audio').forEach(audio=>audio.pause())} onLoadedMetadata={e=>{if(clip&&clip.status!=='ready')e.currentTarget.currentTime=clip.start;}} src={clip?.status!=='ready'&&dubbedPreview?`/api/projects/${p.id}/dubbing/video?v=${encodeURIComponent(p.dubbing?.video_file||'')}`:media(p.id,clip?.status==='ready'?clip.id:'source',clip?.status==='ready'?clip.file:null)} onTimeUpdate={e=>{const video=e.currentTarget;setPlayhead(video.currentTime);if(clip&&clip.status!=='ready'&&video.currentTime>=clip.end&&!video.paused)video.pause();}}/>{!clip&&subtitle&&<div className="live-caption">{subtitle.text}</div>}</div>{!clip&&p.dubbing?.enabled&&p.dubbing.video_file&&<button type="button" className="secondary" onClick={()=>setOriginalPreview(value=>!value)}>{dubbedPreview?'Compare original audio':'Play dubbed video'}</button>}<div className="preview-footer"><span><span className="dot"/>{clip?.status==='ready'?'Preview first · download only if you like it':clip?'Source range only · Render video to preview saved captions/effects':dubbedPreview?'Translated voice · editable captions below':'Source video · editable transcript below'}</span>{clip?.status==='ready'&&<a href={media(p.id,clip.id,clip.file)} download className="primary small"><ArrowDownToLine size={15}/>Download {clip.file?.endsWith('.webm')?'WebM':'MP4'}</a>}</div>{clip?.status==='ready'&&p.has_audio&&<AudioCompare projectId={p.id} clip={clip}/>}<VideoTimeline duration={p.duration} current={playhead} segments={segments} clip={clip} onSeek={value=>{if(player.current)player.current.currentTime=value;}}/><p className="timeline-note">Render to preview edited captions, motion and audio. Download is always manual.</p></section>}
    <section className="workflow-panel"><details open={aiOpen} onToggle={e=>setAiOpen(e.currentTarget.open)}><summary className="ai-workflow-summary"><Sparkles size={17}/>Generate AI clips<span>Quantity, captions and export preferences</span></summary><div className="panel-heading"><h3><Sparkles size={17}/>Your creative toolkit</h3></div><div className="workflow-body"><div className="step-number">01</div><h3>How many clips do you want?</h3><p>Choose a number. Generate distinct highlights from your video, then export them together.</p><GenerationControls project={p} pending={pending} processing={processing} dirty={dirty} onGenerate={generateClips} onShowClips={()=>{setTab('Clips');requestAnimationFrame(()=>document.querySelector('.batch-toolbar')?.scrollIntoView({behavior:'smooth',block:'start'}));}}/><div className="workflow-divider"/><div className="step-number">02</div><h3>Make it your own</h3><p>Select an automatically generated clip to customize its captions and format. Manual clipping is optional.</p><button className="secondary full" onClick={()=>{setClipId(null);setTab('New clip');}}>Create a manual clip<Plus size={16}/></button><div className="privacy-note"><ShieldCheck size={16}/>Your footage stays on this machine.</div></div></details></section></div>
    {!aiOpen&&p.clip_generation&&<section className="generation-feedback success" role="region" aria-label="Clip generation feedback"><strong>{p.clip_generation.created} new clips created</strong>{p.clip_generation.created<p.clip_generation.requested&&<p>{p.clip_generation.shortfall_message||`Only ${p.clip_generation.created} new clips matched the current settings (${p.clip_generation.requested} requested). The requested number is a maximum.`}</p>}<p role="status">{p.clip_generation.message}</p><button type="button" className="secondary" onClick={()=>{setTab('Clips');requestAnimationFrame(()=>document.querySelector('.batch-toolbar')?.scrollIntoView({behavior:'smooth',block:'start'}));}}>Review generated clips<ArrowRight size={15}/></button></section>}
    {reviewing&&<ClipReview projectId={p.id} clips={p.clips} selected={reviewClip} onSelect={setReviewId} onEdit={id=>{setClipId(id);setAiOpen(false);}} pending={pending} processing={processing} onDeleteMany={deleteSelectedClips} onDelete={id=>{void deleteSelectedClips([id]);}}/>}
    <section className="editor-bottom"><div className="tabs">{['Clips','Transcript','New clip'].map(t=><button key={t} onClick={()=>{setTab(t);if(t==='Transcript')setClipId(null);}} className={tab===t?'selected':''}>{t}{t==='Clips'&&<span>{p.clips.length}</span>}{t==='Transcript'&&<span>{segments.length}</span>}</button>)}</div>
      {tab==='Clips'&&<><div className="batch-toolbar"><div><strong>{p.clips.filter(c=>c.status==='ready').length} / {p.clips.length} exports ready</strong><p>{processing?'Processing your clips (up to two renders at a time)…':dirty?'Save subtitle edits before generating or rendering.':'Review your clips or render every draft in one click.'}</p></div><button className="primary small" disabled={pending||processing||dirty||!p.clips.some(c=>['draft','error'].includes(c.status))} onClick={()=>void action(`/projects/${p.id}/clips/render`)}>{processing?<LoaderCircle className="spin" size={15}/>:<Clapperboard size={15}/>}Render all drafts</button></div>{aiOpen&&p.clip_generation&&<div className="generation-summary" role="status">{p.clip_generation.message}</div>}</>}
      {tab==='Clips'&&<><div className={`editor-clips ${reviewing?'review-library-hidden':''}`}>{p.clips.map(c=><button key={c.id} className={`edit-clip ${clipId===c.id?'chosen':''}`} onClick={()=>{setClipId(c.id);if(player.current&&c.status!=='ready')player.current.currentTime=c.start;}}><div className="clip-source-thumbnail" style={{backgroundImage:`url("${media(p.id,'poster')}")`}}><MonitorPlay size={24}/><span>Source footage</span></div><div className="clip-top"><span className="clip-icon"><Film size={18}/></span><span className="status standalone">{busy(c.status)&&<LoaderCircle size={12} className="spin"/>}{c.status}</span></div><h3>{c.title}</h3><p>{time(c.start)} – {time(c.end)}<span>·</span>{time(c.end-c.start)}</p><div className="score">{c.score!==null?<><Sparkles size={13}/> {c.score} {c.selection_evidence?'engagement heuristic':'relevance'}</>:<>Manual selection</>}<ArrowRight size={15}/></div>{c.error&&<small className="error-text">{c.error}</small>}</button>)}</div>{!p.clips.length&&<div className="empty compact"><Film size={25}/><h3>{p.clip_generation?'No new clips matched these settings':'Your generated clips will appear here'}</h3><p>{p.clip_generation?'See the generation result beside the Generate button. Adjust the minimum score or try Explore all suggestions.':'Use Generate to transcribe speech and prepare clip previews automatically.'}</p></div>}{clip?.selection_evidence&&<section className="selection-evidence"><h3>Why this moment?</h3><p>{clip.reason}</p><p>Opening: {clip.selection_evidence.opening_excerpt}</p><div>{Object.entries(clip.selection_evidence.factors).map(([name,value])=><span key={name}>{name.replaceAll('_',' ')}: {value}/100 · </span>)}</div>{clip.selection_evidence.recommendations.map((text,index)=><p key={index}>{text}</p>)}<small>{clip.selection_evidence.limitations}</small></section>}{clip&&<ClipForm key={clip.id+clip.status} project={p} clip={clip} pending={pending} dirty={dirty} onSubmit={body=>action(`/projects/${p.id}/clips/${clip.id}`,body,'PUT')} onRender={()=>void action(`/projects/${p.id}/clips/${clip.id}/render`)} onSaveRender={body=>saveAndRender(clip.id,body)} onApplyAll={applyAll} onDelete={async()=>{if(await deleteSelectedClips([clip.id]))setClipId(null);}} />}</>}
      {tab==='New clip'&&<ClipForm project={p} pending={pending} dirty={dirty} onSubmit={body=>action(`/projects/${p.id}/clips`,body,'POST',()=>setTab('Clips'))}/>}
      {tab==='Transcript'&&<div className="transcript"><TranscriptLanguageControls key={p.id} script={p.caption_script} language={p.speech_language} disabled={pending||processing||dirty} onConvert={script=>action(`/projects/${p.id}/transcript/script`,{caption_script:script})} onTranscribe={(script,language)=>action(`/projects/${p.id}/transcribe`,{redo:true,transcription_mode:'accurate',caption_script:script,speech_language:language})}/><DubbingPanel projectId={p.id} language={p.language} current={p.dubbing} error={p.dubbing_error} disabled={pending||processing||dirty||!p.transcript.length} onApply={(script,enabled,render)=>action(`/projects/${p.id}/dubbing`,{caption_script:script,enabled,auto_render:render})}/><div className="transcript-heading"><p>Edit text and timestamps. Saving marks existing renders as drafts so exports match your edits.</p><button className="primary small" disabled={!dirty||pending||processing} onClick={async()=>{setPending(true);try{await api(`/projects/${p.id}/transcript`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(segments)});setDirty(false);await refresh();notify('Subtitles saved. Render your clips to include these edits.');}catch(e){notify(e instanceof Error?e.message:'Could not save');}finally{setPending(false);}}}><Check size={15}/>Save subtitles</button></div>{!segments.length&&<p className="muted">No speech transcript yet. Transcribe your video, or add subtitle segments manually.</p>}{segments.map((s,index)=><div className="subtitle-row" key={s.id}><button className="subtitle-seek" onClick={()=>{setClipId(null);if(player.current)player.current.currentTime=s.start;}} aria-label={`Seek to ${time(s.start)}`}><MonitorPlay size={17}/></button><label>Start (s)<input type="number" min="0" step="0.01" value={s.start} onChange={e=>{setDirty(true);setSegments(prev=>prev.map((item,i)=>i===index?{...item,start:Number(e.target.value)}:item));}}/></label><label>End (s)<input type="number" min="0" step="0.01" value={s.end} onChange={e=>{setDirty(true);setSegments(prev=>prev.map((item,i)=>i===index?{...item,end:Number(e.target.value)}:item));}}/></label><textarea aria-label={`Subtitle ${index+1}`} value={s.text} maxLength={2000} onChange={e=>{setDirty(true);setSegments(prev=>prev.map((item,i)=>i===index?{...item,text:e.target.value}:item));}}/>{s.source_text&&<small className="translation-source"><strong>Original:</strong> {s.source_text}{s.translation_warning&&<span role="status">{s.translation_warning}</span>}</small>}<button className="icon-button" aria-label={`Remove subtitle ${index+1}`} onClick={()=>{setDirty(true);setSegments(prev=>prev.filter((_,i)=>i!==index));}}><X size={16}/></button></div>)}<button className="secondary" disabled={processing} onClick={()=>{setDirty(true);setSegments(prev=>[...prev,{id:Math.max(-1,...prev.map(s=>s.id))+1,start:0,end:Math.min(3,p.duration),text:''}]);}}><Plus size={15}/>Add subtitle</button></div>}
    </section></div>
  </>;
}

function GenerationControls({project,pending,processing,dirty,onGenerate,onShowClips}:{project:Project;pending:boolean;processing:boolean;dirty:boolean;onGenerate:(count:number,mode:string,selection:'quality'|'all',threshold:number,autoRender:boolean,look:EffectSettings,captionScript:CaptionScript,speechLanguage:SpeechLanguage,minDuration:number,maxDuration:number)=>Promise<Project>;onShowClips:()=>void}) {
  const [count,setCount] = useState(String(project.requested_clip_count??5));
  const [autoCount,setAutoCount]=useState(project.auto_count??false);
  const [minimum,setMinimum]=useState(String(project.min_duration??8));
  const [maximum,setMaximum]=useState(String(project.max_duration??60));
  const [mode,setMode] = useState(project.transcription_mode||'quick');
  const [captionScript,setCaptionScript]=useState<CaptionScript>(project.caption_script||'original');
  const [speechLanguage,setSpeechLanguage]=useState<SpeechLanguage>(project.speech_language||'auto');
  const [selection,setSelection]=useState<'quality'|'all'>(project.selection_mode||'quality');
  const [threshold,setThreshold]=useState(project.minimum_score??70);
  const [autoRender,setAutoRender]=useState(true);
  const [look,setLook]=useState<EffectSettings>({...defaultEffects,...project.default_effects,sticker:'none',sticker_enabled:false});
  const [submitting,setSubmitting]=useState(false);
  const [awaitingJob,setAwaitingJob]=useState(false);
  const [feedback,setFeedback]=useState<{kind:'working'|'success'|'empty'|'error';message:string;created?:number}|null>(project.clip_generation?{kind:project.clip_generation.created?'success':'empty',message:project.clip_generation.message,created:project.clip_generation.created}:null);
  const requestActive=useRef(false);
  const baselineBatch=useRef<string|undefined>(undefined);
  function showResult(result:Project){
    const generation=result.clip_generation;
    if(!generation)throw new Error('The server did not return a clip-generation result. Please retry.');
    setFeedback({kind:generation.created?'success':'empty',message:generation.message,created:generation.created});
  }
  useEffect(()=>{
    if(!awaitingJob)return;
    if(project.status==='error'){
      setFeedback({kind:'error',message:project.error||'Processing failed. Retry generation.'});
      setAwaitingJob(false);requestActive.current=false;
    }else if(!busy(project.status)&&project.clip_generation&&project.clip_generation.batch_id!==baselineBatch.current){
      showResult(project);setAwaitingJob(false);requestActive.current=false;
    }
  },[awaitingJob,project.status,project.error,project.clip_generation]);
  const countInput=useRef<HTMLInputElement>(null);
  const number = Number(count);
  const valid = validDuration(minimum,maximum)&&(autoCount||Number.isInteger(number)&&number>=1&&number<=100)&&Number.isInteger(threshold)&&threshold>=0&&threshold<=100;
  async function startGeneration(override?:'quality'|'all'){
    if(requestActive.current||pending||processing||dirty||!valid)return;
    requestActive.current=true;setSubmitting(true);setFeedback({kind:'working',message:project.transcript.length?'Analyzing your saved transcript…':'Queuing audio transcription…'});
    baselineBatch.current=project.clip_generation?.batch_id;
    if(override)setSelection(override);
    try{
      const result=await onGenerate(autoCount?0:number,mode,override||selection,threshold,autoRender,look,captionScript,speechLanguage,Number(minimum),Number(maximum));
      if(busy(result.status)){
        setAwaitingJob(true);setFeedback({kind:'working',message:result.status==='analyzing'?'Request accepted. Analyzing saved speech and source signals...':'Request accepted. Transcribing audio before selecting clips...'});
      }else{showResult(result);requestActive.current=false;}
    }catch(error){
      setFeedback({kind:'error',message:error instanceof Error?error.message:'Could not generate clips. Please retry.'});
      requestActive.current=false;setAwaitingJob(false);
    }finally{setSubmitting(false);}
  }
  return <div className="generation-controls"><label className="check-field"><input type="checkbox" aria-label="Automatic clip quantity" checked={autoCount} disabled={pending||processing} onChange={e=>setAutoCount(e.target.checked)}/>Auto quantity - only distinct qualified moments (maximum 100)</label><label>Selection mode<select aria-label="Selection mode" value={selection} disabled={pending||processing} onChange={e=>setSelection(e.target.value as typeof selection)}><option value="quality">Quality first · only qualified moments</option><option value="all">Explore all · legacy suggestions</option></select></label>{selection==='quality'&&<label>Minimum engagement score<input aria-label="Minimum engagement score" type="number" min="0" max="100" step="1" value={threshold} disabled={pending||processing} onChange={e=>setThreshold(Number(e.target.value))}/><small>Heuristic score using speech and available media measurements, not a probability of virality. Stronger threshold = fewer clips.</small></label>}<label>Number of clips<input ref={countInput} aria-label="Number of clips" aria-describedby="custom-clip-help" placeholder="e.g. 7 or 25" type="number" min="1" max="100" step="1" value={count} disabled={pending||processing||autoCount} onChange={e=>setCount(e.target.value)}/><small id="custom-clip-help">Choose a maximum from 1 to 100. If you request 30 and only 4 distinct moments pass the duration and quality rules, you receive 4 with an explanation. Longer videos do not guarantee more qualified clips.</small>{validDuration(minimum,maximum)&&!autoCount&&number>Math.max(1,Math.floor(project.duration/Number(minimum)))&&<small role="status">Duration budget: at most {Math.max(1,Math.floor(project.duration/Number(minimum)))} separate clips fit at your minimum duration. Quality filters may reduce this further; shorten the duration to request more clips.</small>}</label><div className="count-presets">{[5,10,30,100].map(value=><button type="button" aria-label={`Choose ${value} clips`} aria-pressed={number===value} disabled={pending||processing} className={number===value?'selected':''} key={value} onClick={()=>{setAutoCount(false);setCount(String(value));}}>{value}</button>)}<button type="button" aria-label="Enter a custom clip count" disabled={pending||processing} onClick={()=>{setAutoCount(false);requestAnimationFrame(()=>{countInput.current?.focus();countInput.current?.select();});}}>Custom</button></div><ClipDuration minimum={minimum} maximum={maximum} onChange={(a,b)=>{setMinimum(a);setMaximum(b);}} disabled={pending||processing}/><details className="generation-look"><summary>Clip style & export settings</summary><label>Generated caption design<select aria-label="Generated caption design" value={look.style} disabled={pending||processing} onChange={e=>setLook(prev=>({...prev,style:e.target.value as EffectSettings['style']}))}>{subtitleStyles.map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label><label>Generated frame format<select aria-label="Generated frame format" value={look.aspect} disabled={pending||processing} onChange={e=>setLook(prev=>({...prev,aspect:e.target.value as EffectSettings['aspect']}))}>{[['original','Original ratio'],['vertical','9:16 Shorts'],['square','1:1 Square'],['landscape','16:9 Landscape'],['portrait','4:5 Portrait']].map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label><label>Generated framing<select aria-label="Generated framing" value={look.framing} disabled={pending||processing} onChange={e=>setLook(prev=>({...prev,framing:e.target.value as EffectSettings['framing']}))}><option value="follow">Full screen - follow visible face</option><option value="crop">Full screen - fixed crop</option><option value="fit">Keep full source - allow padding</option></select></label><label>Generated quality<select aria-label="Generated quality" value={look.render_quality} disabled={pending||processing} onChange={e=>setLook(prev=>({...prev,render_quality:e.target.value as EffectSettings['render_quality']}))}><option value="fast">480p Fast</option><option value="standard">720p HD</option><option value="high">High / native original</option></select></label><label>Generated voice<select aria-label="Generated voice" value={look.voice_effect} disabled={pending||processing} onChange={e=>setLook(prev=>({...prev,voice_effect:e.target.value as EffectSettings['voice_effect']}))}>{[['none','Original'],['deep','Deep'],['high','High pitch'],['radio','Radio'],['echo','Echo'],['mute','Mute']].map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label></details><label className="check-field"><input type="checkbox" checked={autoRender} disabled={pending||processing} onChange={e=>setAutoRender(e.target.checked)}/>Prepare generated previews automatically</label><SubtitleOptions script={captionScript} language={speechLanguage} onScript={setCaptionScript} onLanguage={setSpeechLanguage} disabled={pending||processing} sourceDisabled={project.transcript.length>0}/><label>Transcription speed<select aria-label="Transcription speed" value={mode} disabled={pending||processing||project.transcript.length>0} onChange={e=>setMode(e.target.value as TranscriptionMode)}>{recognitionChoices(captionScript,speechLanguage).map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label><button className="primary full" aria-busy={submitting||awaitingJob||processing} disabled={pending||processing||dirty||!valid||submitting||awaitingJob} onClick={()=>void startGeneration()}>{pending||submitting||awaitingJob||processing?<LoaderCircle size={16} className="spin"/>:<WandSparkles size={16}/ >}{submitting?'Generating clips…':busy(project.status)?`${project.status}…`:awaitingJob?'Preparing clips…':processing?'Rendering previews…':`Generate ${autoCount?'AI':valid?number:'your'} new clips`}</button>{feedback&&<section className={`generation-feedback ${feedback.kind}`} role="region" aria-label="Clip generation feedback" aria-live="polite"><strong>{feedback.kind==='error'?'Generation failed':feedback.kind==='working'?'Processing your request':`${feedback.created} new clips created`}</strong>{(feedback.kind==='success'||feedback.kind==='empty')&&project.clip_generation&&Number(feedback.created)<project.clip_generation.requested&&<p>{project.clip_generation.shortfall_message||`Only ${feedback.created} new clips matched the current settings (${project.clip_generation.requested} requested). The requested number is a maximum.`}</p>}<p role={feedback.kind==='error'?'alert':undefined}>{awaitingJob&&project.status==='transcribing'?'Transcribing your audio. The first run processes the full video; progress appears below.':feedback.message}</p>{feedback.kind==='empty'&&<p>Naye clips nahi milay. Count maximum hai; purane clips aur selection rules ki wajah se kam ya zero clips mil sakti hain.</p>}{(feedback.kind==='success'||feedback.kind==='empty')&&project.clips.length>0&&<button className="secondary" type="button" onClick={onShowClips}>Review {feedback.kind==='success'?'generated':'existing'} clips<ArrowRight size={14}/></button>}{feedback.kind==='empty'&&selection==='quality'&&<><button className="secondary" type="button" disabled={pending||processing||submitting||awaitingJob||dirty} onClick={()=>void startGeneration('all')}>Try Explore all suggestions</button><small>Includes lower-scoring moments; more clips are not guaranteed.</small></>}</section>}{project.status==='transcribing'&&<div className="transcription-progress"><progress value={project.transcription_progress||0} max="100"/><span>{project.transcription_progress||0}% of source transcribed</span></div>}<small>{!valid?'Choose 1-100 clips and a valid 3-180 second duration range.':dirty?'Save your subtitle edits first.':project.transcript.length?'Uses your saved transcript; existing clips stay intact.':'Runs on this machine. Each model downloads once, then stays cached.'}</small><small>First generation transcribes the whole source, even for 5 clips. Once saved, the transcript is reused for new clip counts.</small><small>Quality first ranks opening hooks, complete thoughts, payoff markers and pacing from the transcript. The count is a maximum; weak or repeated moments may produce zero clips. Review context before publishing.</small></div>;
}


export {Editor as ProjectEditor,releasePreviewMedia};
