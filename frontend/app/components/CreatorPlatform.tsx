'use client';
import Link from 'next/link';
import {useCallback,useEffect,useRef,useState} from 'react';
import {ArrowRight,Clapperboard,FolderOpen,Home,LoaderCircle,MessageSquare,RefreshCw,ShieldCheck,Sparkles,Trash2,UploadCloud,Video,X} from 'lucide-react';
import {BRAND} from '../../lib/brand';
import {ensureGuestSession,decodeApiResponse,apiErrorMessage} from '../../lib/api';
import {platformApi,editorUrl,clock,type WorkspaceProject} from '../../lib/platform';
import LinkImporter from './LinkImporter';
import {ProjectEditor,releasePreviewMedia} from '../LegacyWorkspace';
import WizardWorkspace from './WizardWorkspace';
import LocalStudio from './LocalStudio';
import SourceImage from './SourceImage';

export type PlatformView='Create'|'Explore'|'Wizard'|'Studio';
const routes:Record<PlatformView,string>={Create:'/dashboard',Explore:'/explore',Wizard:'/wizard',Studio:'/studio'};
export default function CreatorPlatform({view='Create',seedUrl='',seedPrompt='',seedProject=''}:{view?:PlatformView;seedUrl?:string;seedPrompt?:string;seedProject?:string}){
 const picker=useRef<HTMLInputElement>(null);
 const [activeProject,setActiveProject]=useState(seedProject),[recovering,setRecovering]=useState(false);const workArea=useRef<HTMLElement>(null);
 function openProject(id:string){setActiveProject(id);const url=new URL(window.location.href);url.searchParams.set('project',id);window.history.replaceState(null,'',url);requestAnimationFrame(()=>workArea.current?.scrollIntoView({behavior:'smooth',block:'start'}));}
 function closeProject(){setActiveProject('');const url=new URL(window.location.href);url.searchParams.delete('project');window.history.replaceState(null,'',url);}
 useEffect(()=>{setActiveProject(seedProject);},[seedProject,view]);

 const [projects,setProjects]=useState<WorkspaceProject[]>([]),[loaded,setLoaded]=useState(false),[error,setError]=useState(''),[refreshError,setRefreshError]=useState(''),[uploading,setUploading]=useState(false),[progress,setProgress]=useState(0);
 const refresh=useCallback(async()=>{try{setProjects(await platformApi<WorkspaceProject[]>('/projects'));setLoaded(true);setRefreshError('');}catch(e){setRefreshError(apiErrorMessage(e,'Could not load projects.'));}},[]);
 useEffect(()=>{void refresh();const t=setInterval(()=>void refresh(),5000);return()=>clearInterval(t);},[refresh]);
 async function upload(file?:File){
  if(!file||uploading)return;if(file.size>2*1024**3){setError('Choose a video up to 2 GB.');return;}
  setUploading(true);setProgress(0);setError('');
  try{await ensureGuestSession();}catch(e){setError(apiErrorMessage(e,'Could not start a private session.'));setUploading(false);return;}
  const xhr=new XMLHttpRequest();xhr.open('POST','/api/projects');xhr.upload.onprogress=e=>{if(e.lengthComputable)setProgress(Math.round(e.loaded/e.total*100));};
  xhr.onload=()=>{setUploading(false);try{const p=decodeApiResponse<WorkspaceProject>(xhr.responseText,xhr.status);setProjects(prev=>[p,...prev.filter(x=>x.id!==p.id)]);openProject(p.id);}catch(e){setError(e instanceof Error?e.message:'Upload failed.');}};
  xhr.onerror=()=>{setUploading(false);setError('The video server could not be reached. Retry your upload.');};
  const form=new FormData();form.append('file',file);xhr.send(form);
 }
 async function remove(p:WorkspaceProject){
  if(!window.confirm(`Delete "${p.name}" and all its videos, clips and subtitles?`))return;
  const restorePreview=releasePreviewMedia();
  try{await platformApi('/projects/'+p.id,{method:'DELETE'});if(activeProject===p.id)closeProject();await refresh();}catch(e){setError(e instanceof Error?e.message:'Deletion failed.');}finally{requestAnimationFrame(restorePreview);}
 }
 const clipCount=projects.reduce((n,p)=>n+p.clips.length,0),readyCount=projects.reduce((n,p)=>n+p.clips.filter(c=>c.status==='ready').length,0);
 return <div className="creator-platform" data-active-project={view==='Create'&&!!activeProject}>
  <input ref={picker} type="file" accept="video/*,.mkv,.mov,.webm" hidden onChange={e=>{void upload(e.target.files?.[0]);e.target.value='';}}/>
  <header className="platform-header"><Link className="platform-brand" href="/dashboard" onClick={closeProject}><span><Clapperboard size={22}/></span>{BRAND}<small>AI</small></Link><nav aria-label="Creator navigation">{(Object.keys(routes) as PlatformView[]).map(name=><Link key={name} href={routes[name]} onClick={()=>{if(name==='Create')closeProject();}} aria-current={view===name?'page':undefined}>{name}</Link>)}</nav><Link className="workspace-link" href="/workspace"><ShieldCheck size={16}/><span>Private workspace</span></Link></header>
  <aside className="platform-sidebar" aria-label="Workspace sections">
   <Link href="/dashboard" onClick={closeProject} aria-current={view==='Create'&&!activeProject?'page':undefined}><Home size={21}/><span>Home</span></Link>
   <Link href="/dashboard#project-library" onClick={closeProject}><FolderOpen size={21}/><span>Library</span></Link>
   <Link href="/wizard" aria-current={view==='Wizard'?'page':undefined}><MessageSquare size={21}/><span>Wizard</span></Link>
   <Link href="/studio" aria-current={view==='Studio'?'page':undefined}><Video size={21}/><span>Studio</span></Link>
   <span className="platform-sidebar-privacy"><ShieldCheck size={17}/><span>Private<br/>and local</span></span>
  </aside>
  <main className="platform-main">
   {(error||refreshError)&&<div className="platform-alert" role="alert">{error||refreshError}<button aria-label="Dismiss message" onClick={()=>{setError('');setRefreshError('');}}><X size={17}/></button></div>}
   {uploading&&<div className="platform-upload" role="status"><LoaderCircle className="spin" size={18}/>{progress===100?'Validating video and creating source preview…':`Uploading ${progress}%`}<progress value={progress} max={100}/></div>}
   {view==='Create'&&<>
    <section className="platform-create-hero" hidden={!!activeProject} aria-labelledby="platform-clipping-title"><div className="platform-clipping-intro"><span className="platform-eyebrow">YOUR VIDEO. YOUR MOMENTS.</span><h1 id="platform-clipping-title">AI Clipping</h1><p>Find the moments worth sharing. Create clips for Shorts, Reels and TikTok.</p></div><LinkImporter key={seedUrl} initialUrl={seedUrl} studio onUpload={()=>picker.current?.click()} onProject={async id=>{await refresh();openProject(id);}}/><p className="platform-source-limits">Supported public video links or your own video file. Up to 2 GB / 4 hours.<br/>Review your previews here, then download only the clips you choose.</p></section>
    {view==='Create'&&activeProject&&<section ref={workArea} className="platform-work-area" aria-label="Video processing and clips">
      {projects.find(p=>p.id===activeProject)?(()=>{const p=projects.find(p=>p.id===activeProject)!;return <>
        <header><h2>Your video & clips</h2><button type="button" onClick={closeProject}>Close video <X size={16}/></button></header>
        {p.error&&p.source_transcript?.length? <div className="platform-alert"><span>Source video and saved speech are available. Recover them without downloading or transcribing again.</span><button disabled={recovering} onClick={async()=>{setRecovering(true);try{await platformApi(`/projects/${p.id}/recover`,{method:'POST'});await refresh();}catch(e){setError(e instanceof Error?e.message:'Recovery failed.');}finally{setRecovering(false);}}}>{recovering?'Recovering...':'Recover saved speech & generate'}</button></div>:null}
        <div className="shell inline-platform-editor"><div className="content"><ProjectEditor key={p.id} project={p} onBack={closeProject} refresh={refresh} notify={setError}/></div></div>
      </>;})():<p role="status">{loaded?'This project is not available in this private workspace.':'Loading your video...'}</p>}
    </section>}
    <section className="platform-tools" aria-label="Creator tools"><Link href="/studio"><Video size={24}/><h2>Make a local video</h2><p>Animate a photo or turn your words into a styled video.</p><span>Open Studio <ArrowRight size={17}/></span></Link><Link href="/wizard"><MessageSquare size={24}/><h2>Ask the Wizard</h2><p>Generate, caption and trim clips with supported local commands.</p><span>Open Wizard <ArrowRight size={17}/></span></Link><Link href="/explore"><Sparkles size={24}/><h2>Find your next source</h2><p>Browse video discovery or work with your existing projects.</p><span>Explore <ArrowRight size={17}/></span></Link></section>
    <section className="platform-stats" aria-label="Workspace statistics">{[['Projects',projects.length],['Clips created',clipCount],['Exports ready',readyCount]].map(([name,value])=><article key={name}><span>{name}</span><strong>{loaded?value:'—'}</strong><small>Actual private workspace data</small></article>)}</section>
    <section className="platform-projects" id="project-library"><header><div><h2>Recent projects</h2><p>Your source videos and generated clips, in one place.</p></div><Link href="/workspace">View all <ArrowRight size={16}/></Link></header>{!loaded?<p role="status">Loading your workspace...</p>:!projects.length?<div className="platform-empty"><FolderOpen size={30}/><h3>No projects yet</h3><p>Paste a supported public link above or upload your video.</p><button onClick={()=>picker.current?.click()}><UploadCloud size={17}/>Upload video</button></div>:<div className="platform-project-grid">{projects.slice(0,6).map(p=><article key={p.id}><button className="platform-open-project" onClick={()=>openProject(p.id)}><div className="platform-project-poster"><img src={`/api/projects/${p.id}/media/poster`} alt=""/><span>{clock(p.duration)}</span></div><h3>{p.name}</h3><p><span className={`platform-project-state ${p.status}`}>{p.status}</span>{p.clips.length} clips</p></button><button type="button" className="platform-delete" aria-label={`Delete project ${p.name}`} disabled={['queued','transcribing','analyzing'].includes(p.status)||p.clips.some(c=>['queued','rendering'].includes(c.status))} onClick={()=>void remove(p)}><Trash2 size={16}/>Delete</button></article>)}</div>}</section>
   </>}
   {view==='Explore'&&<Explore projects={projects}/>}
   {view==='Wizard'&&<WizardWorkspace projects={projects} refresh={refresh} seedPrompt={seedPrompt}/>}
   {view==='Studio'&&<LocalStudio refreshProjects={refresh}/>}
  </main>
 </div>;
}

type DiscoveryItem={id:string;title:string;channel:string;url:string;thumbnail:string;duration:number|null;views:number|null;views_per_hour:number|null};
type Discovery={items:DiscoveryItem[];observed_at:number;message:string;stale:boolean;source:string};
function Explore({projects}:{projects:WorkspaceProject[]}){
 const [category,setCategory]=useState('All'),[source,setSource]=useState<'library'|'public'>('public'),[data,setData]=useState<Discovery|null>(null),[loading,setLoading]=useState(false),[error,setError]=useState('');
 const sequence=useRef(0);
 async function search(cat:string,force=false){const current=++sequence.current;setLoading(true);setData(null);setError('');try{const result=await platformApi<Discovery>(`/discover?category=${encodeURIComponent(cat)}&refresh=${force}`);if(sequence.current===current)setData(result);}catch(e){if(sequence.current===current)setError(e instanceof Error?e.message:'Discovery unavailable.');}finally{if(sequence.current===current)setLoading(false);}}
 useEffect(()=>{if(source==='public')void search(category);return()=>{sequence.current++;};},[source,category]);
 return <section className="platform-explore"><div className="platform-page-heading"><div><h1>Explore</h1><p>Discover source videos, or pick up a project of your own.</p></div><button disabled={loading} onClick={()=>source==='public'?void search(category,true):window.location.reload()}><RefreshCw size={17} className={loading?'spin':''}/>Refresh</button></div>
  <div className="platform-pills"><button aria-pressed={source==='library'} onClick={()=>setSource('library')}>Your library</button><button aria-pressed={source==='public'} onClick={()=>setSource('public')}>YouTube discovery</button></div>
  {source==='public'?<><p className="platform-note">Public relevance search, not a verified trending chart. Import availability depends on the source website. No view counts or growth rates are invented.</p><div className="platform-pills" aria-label="Discovery categories">{['All','Podcasts','Interviews','Business','Comedy','True crime','News','Education','Sports','Gaming','Fitness','Tech'].map(c=><button key={c} aria-pressed={category===c} onClick={()=>setCategory(c)}>{c}</button>)}</div>{loading&&<p role="status"><LoaderCircle className="spin" size={17}/>Reading public video metadata…</p>}{error&&<p className="platform-alert" role="alert">{error}</p>}{data&&!loading&&<><p className="platform-note">{data.message} Updated {new Date(data.observed_at*1000).toLocaleString()}{data.stale?' · Last successful cache':''}</p><div className="platform-discovery-grid">{data.items.map(v=><article key={v.id}><div><SourceImage src={v.thumbnail} youtubeId={v.id}/>{v.duration!=null&&<span>{clock(v.duration)}</span>}<Link href={'/dashboard?url='+encodeURIComponent(v.url)}>Get clips <ArrowRight size={15}/></Link></div><h3>{v.title}</h3><p>{v.channel}</p><small>{v.views!=null?v.views.toLocaleString()+' views':'View count unavailable'}{v.views_per_hour!=null?' · '+v.views_per_hour.toLocaleString()+' measured views/hour':''}</small></article>)}</div>{!data.items.length&&<p>No sources returned. Try another category or paste a link on Create.</p>}</>}</>:<div className="platform-project-grid">{projects.map(p=><article key={p.id}><Link href={editorUrl(p.id)}><img src={`/api/projects/${p.id}/media/poster`} alt=""/><h3>{p.name}</h3><p>{clock(p.duration)} · {p.clips.length} clips</p><span>Open project <ArrowRight size={16}/></span></Link></article>)}{!projects.length&&<div className="platform-empty"><h2>Your library is empty</h2><p>Import or upload a source to begin.</p><Link href="/dashboard">Create clips <ArrowRight size={16}/></Link></div>}</div>}
 </section>;
}
