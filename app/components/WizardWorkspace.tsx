'use client';
import Link from 'next/link';
import {useEffect,useRef,useState} from 'react';
import {ArrowRight,Check,LoaderCircle,Plus,Send,Sparkles} from 'lucide-react';
import {platformApi,jsonBody,editorUrl,type WorkspaceProject} from '../../lib/platform';

type Message={role:'user'|'assistant';text:string};
type Plan={operation:'import'|'generate'|'edit'|'render';body:Record<string,unknown>;description:string};
export default function WizardWorkspace({projects,refresh,seedPrompt=''}:{projects:WorkspaceProject[];refresh:()=>Promise<void>;seedPrompt?:string}){
 const [projectId,setProjectId]=useState(''),[clipId,setClipId]=useState(''),[input,setInput]=useState(seedPrompt),[messages,setMessages]=useState<Message[]>([]),[plan,setPlan]=useState<Plan|null>(null),[pending,setPending]=useState(false),[error,setError]=useState(''),[historyReady,setHistoryReady]=useState(false),[importId,setImportId]=useState<string|null>(null);
 const composer=useRef<HTMLTextAreaElement>(null);
 const project=projects.find(p=>p.id===projectId),clip=project?.clips.find(c=>c.id===clipId);
 useEffect(()=>{void platformApi<{messages:Message[]}>('/wizard/history').then(r=>{setMessages(r.messages);setHistoryReady(true);}).catch(e=>setError(e.message));},[]);
 useEffect(()=>{if(!projectId&&projects.length)setProjectId(projects[0].id);},[projectId,projects]);
 useEffect(()=>{if(project&&!project.clips.some(c=>c.id===clipId))setClipId(project.clips[0]?.id||'');},[project,clipId]);
 useEffect(()=>{if(!importId)return;let live=true;const timer=setInterval(()=>{void platformApi<{status:string;message:string;error?:string;project_id?:string}>('/imports/'+importId).then(job=>{if(!live)return;if(job.status==='error'){setError(job.error||job.message);setImportId(null);}else if(job.project_id){setProjectId(job.project_id);void refresh();if(job.status==='ready')setImportId(null);}}).catch(e=>{if(live)setError(e.message);});},1800);return()=>{live=false;clearInterval(timer);};},[importId,refresh]);
 async function save(next:Message[]){setMessages(next.slice(-80));try{await platformApi('/wizard/history',jsonBody({messages:next.slice(-80)},'PUT'));}catch{setError('The action completed, but chat history could not be saved.');}}
 async function submit(){if(!input.trim()||pending||!historyReady)return;setPending(true);setPlan(null);setError('');const text=input.trim();setInput('');const next:Message[]=[...messages,{role:'user',text}];try{const p=await platformApi<Plan>('/wizard/plan',jsonBody({message:text,project_id:projectId||null,clip_id:clipId||null}));setPlan(p);await save([...next,{role:'assistant',text:'Ready to run: '+p.description}]);}catch(e){const text=e instanceof Error?e.message:'Could not interpret this command.';setError(text);await save([...next,{role:'assistant',text}]);}finally{setPending(false);}}
 async function run(){if(!plan||pending)return;setPending(true);setError('');try{
  if(plan.operation==='import'){
   const job=await platformApi<{id:string}>('/imports',jsonBody({...plan.body,caption_script:'original',render_quality:'fast'}));setImportId(job.id);await save([...messages,{role:'assistant',text:'Import queued. Real download, transcription and rendering are running; results appear below when available.'}]);
  }else{
   const latest=await platformApi<WorkspaceProject>('/projects/'+projectId);
   if(plan.operation==='generate')await platformApi(`/projects/${projectId}/${latest.transcript.length?'highlights':'transcribe'}`,jsonBody({...plan.body,caption_script:latest.caption_script||'original',speech_language:latest.speech_language||'auto',generated_settings:latest.default_effects||{render_quality:'fast'}}));
   else{
    const latestClip=latest.clips.find(c=>c.id===clipId);if(!latestClip)throw new Error('Select an existing clip.');
    if(plan.operation==='edit')await platformApi(`/projects/${projectId}/clips/${clipId}`,jsonBody({...latestClip,...plan.body},'PUT'));
    await platformApi(`/projects/${projectId}/clips/${clipId}/render`,{method:'POST'});
   }
   await refresh();await save([...messages,{role:'assistant',text:'Request accepted. Check actual processing status below; watch the finished preview before downloading.'}]);
  }
  setPlan(null);
 }catch(e){setError(e instanceof Error?e.message:'The action could not finish.');}finally{setPending(false);}}
 async function clear(){setPending(true);try{await platformApi('/wizard/history',{method:'DELETE'});setMessages([]);setPlan(null);setError('');}catch(e){setError(e instanceof Error?e.message:'Could not clear chat.');}finally{setPending(false);}}
 const templates=[['Create highlights','generate 5 clips, 15-30 seconds'],['Word-by-word look','captions yellow'],['Resize for Shorts','vertical'],['Adjust caption size','font size 72'],['Trim a source range','trim 2-15'],['Change playback speed','speed 1.2x']];
 const active=!!project&&(['queued','transcribing','analyzing'].includes(project.status)||project.clips.some(c=>['queued','rendering'].includes(c.status)));
 return <section className="platform-wizard"><aside><button onClick={()=>void clear()} disabled={pending||!historyReady}><Plus size={17}/>New chat</button><p>History stays in your private guest workspace.</p><Link href="/dashboard">Import a source <ArrowRight size={15}/></Link></aside><div>
  <div className="platform-page-heading"><div><h1>What should we make?</h1><p>Clip, caption and trim with supported local commands.</p></div></div>
  <p className="platform-note">Use the supported commands below. Wizard does not interpret arbitrary requests. Review each action before running it; your edits are processed locally.</p>
  <div className="wizard-context"><label>Project<select aria-label="Wizard project" value={projectId} disabled={pending||!!plan} onChange={e=>{setProjectId(e.target.value);setClipId('');}}><option value="">Choose a project</option>{projects.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select></label><label>Clip<select aria-label="Wizard clip" value={clipId} disabled={pending||!!plan||!project?.clips.length} onChange={e=>setClipId(e.target.value)}><option value="">Choose a clip</option>{project?.clips.map(c=><option key={c.id} value={c.id}>{c.title}</option>)}</select></label></div>
  {messages.length>0&&<div className="wizard-messages" role="log" aria-label="Wizard conversation">{messages.map((m,i)=><article key={i} className={m.role}><small>{m.role==='user'?'You':'Local Wizard'}</small><p>{m.text}</p></article>)}</div>}
  {error&&<p className="platform-alert" role="alert">{error}</p>}
  {plan&&<div className="wizard-plan" role="region" aria-label="Proposed editing action"><strong><Sparkles size={17}/>Review action</strong><p>{plan.description}</p><button disabled={pending||active} onClick={()=>void run()}>{pending?<LoaderCircle className="spin" size={17}/>:<Check size={17}/>}Run this action</button><button className="platform-secondary" disabled={pending} onClick={()=>setPlan(null)}>Discard</button></div>}
  <form className="wizard-composer" onSubmit={e=>{e.preventDefault();void submit();}}><label htmlFor="wizard-message">Your command</label><textarea ref={composer} id="wizard-message" maxLength={2000} value={input} disabled={pending} onChange={e=>setInput(e.target.value)} placeholder="Generate 5 clips, 15-30 seconds — or paste a video link"/><button type="submit" disabled={pending||!input.trim()||!historyReady}>{pending?<LoaderCircle className="spin" size={18}/>:<Send size={18}/>}Review command</button></form>
  {(active||importId)&&<p role="status" className="platform-note"><LoaderCircle className="spin" size={16}/>{project?.processing_message||project?.status||'Importing source'} · Ready previews: {project?.clips.filter(c=>c.status==='ready').length||0}</p>}
  {project&&<div className="wizard-results"><h2>Project results</h2>{project.error&&<p role="alert">{project.error}</p>}<Link href={editorUrl(project.id,clip?.id)}>Open preview & editor <ArrowRight size={16}/></Link>{clip?.status==='ready'&&<video key={clip.file} src={`/api/projects/${project.id}/media/${clip.id}?v=${encodeURIComponent(clip.file||'')}`} controls playsInline preload="metadata"/>}{clip?.status==='ready'&&<a href={`/api/projects/${project.id}/media/${clip.id}?v=${encodeURIComponent(clip.file||'')}`} download>Download MP4</a>}</div>}
  <h2>Command ideas</h2><div className="wizard-ideas">{templates.map(([name,command])=><button key={name} disabled={pending} onClick={()=>{setInput(command);composer.current?.focus();}}><span><Sparkles size={26}/></span><strong>{name}</strong><small>{command}</small><em>Use command <ArrowRight size={14}/></em></button>)}</div>
 </div></section>;
}
