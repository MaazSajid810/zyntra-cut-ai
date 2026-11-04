'use client';

import {useEffect,useRef,useState} from 'react';
import {ArrowDownToLine,ArrowRight,Film,LoaderCircle,Trash2} from 'lucide-react';
import {decodeApiResponse,guestFetch} from '../../lib/api';
import {type Clip} from '../../lib/editor';

type LibraryProject={id:string;name:string;status:string;clips:Clip[]};
type Row={project:LibraryProject;clip:Clip;key:string;locked:boolean};
const busy=(status:string)=>['queued','transcribing','analyzing','rendering'].includes(status);
const time=(seconds:number)=>`${Math.floor(seconds/60)}:${Math.floor(seconds%60).toString().padStart(2,'0')}`;

export default function ClipLibrary({projects,query,exportsOnly,onOpen,onDeleted}:{projects:LibraryProject[];query:string;exportsOnly:boolean;onOpen:(projectId:string,clipId:string)=>void;onDeleted:()=>Promise<void>}){
  const [selected,setSelected]=useState<Set<string>>(new Set());
  const [deleting,setDeleting]=useState(false);
  const [completed,setCompleted]=useState(0);
  const [total,setTotal]=useState(0);
  const [feedback,setFeedback]=useState<{message:string;errors:string[]}|null>(null);
  const running=useRef(false);
  const selectAll=useRef<HTMLInputElement>(null);
  const rows:Row[]=projects.flatMap(project=>{
    const locked=busy(project.status)||project.clips.some(clip=>busy(clip.status));
    return project.clips.filter(clip=>(!exportsOnly||clip.status==='ready')&&`${project.name} ${clip.title}`.toLowerCase().includes(query.toLowerCase())).map(clip=>({project,clip,key:`${project.id}/${clip.id}`,locked}));
  });
  const eligible=rows.filter(row=>!row.locked);
  const chosen=eligible.filter(row=>selected.has(row.key));
  const allChosen=eligible.length>0&&chosen.length===eligible.length;
  const eligibleKeys=eligible.map(row=>row.key).join('|');
  useEffect(()=>{setSelected(new Set());},[query,exportsOnly]);
  useEffect(()=>{const available=new Set(eligibleKeys.split('|'));setSelected(previous=>new Set([...previous].filter(key=>available.has(key))));},[eligibleKeys]);
  useEffect(()=>{if(selectAll.current)selectAll.current.indeterminate=chosen.length>0&&!allChosen;},[chosen.length,allChosen]);

  async function remove(targets:Row[]){
    if(running.current||!targets.length)return;
    const question=targets.length===1?`Delete "${targets[0].clip.title}" and all its exported versions?`:`Delete ${targets.length} selected clips and all their exported versions?`;
    if(!window.confirm(`${question} Source videos and other clips will stay. This cannot be undone.`))return;
    running.current=true;setDeleting(true);setCompleted(0);setTotal(targets.length);setFeedback(null);
    const removed=new Set<string>(),errors:string[]=[];
    try{
      for(const row of targets){
        try{
          const response=await guestFetch(`/api/projects/${row.project.id}/clips/${row.clip.id}`,{method:'DELETE'});
          decodeApiResponse(await response.text(),response.status);
          removed.add(row.key);
        }catch(error){errors.push(`${row.clip.title}: ${error instanceof Error?error.message:'Deletion failed. Please retry.'}`);}
        setCompleted(value=>value+1);
      }
      setSelected(previous=>new Set([...previous].filter(key=>!removed.has(key))));
      await onDeleted();
      setFeedback({message:`${removed.size} ${removed.size===1?'clip':'clips'} deleted.${errors.length?` ${errors.length} could not be deleted; retry those clips.`:''}`,errors});
    }finally{running.current=false;setDeleting(false);}
  }

  return <div className="clip-library">
    {rows.length>0&&<section className="clip-selection-toolbar" aria-label="Clip selection">
      <label className="clip-select-all"><input ref={selectAll} type="checkbox" checked={allChosen} disabled={deleting||!eligible.length} onChange={event=>setSelected(event.target.checked?new Set(eligible.map(row=>row.key)):new Set())}/>Select all visible clips</label>
      <span>{chosen.length} selected</span>
      {chosen.length>0&&<button type="button" className="text-button" disabled={deleting} onClick={()=>setSelected(new Set())}>Clear selection</button>}
      <button type="button" className="clip-delete-button" disabled={deleting||!chosen.length} onClick={()=>void remove(chosen)}>{deleting?<LoaderCircle size={15} className="spin"/>:<Trash2 size={15}/>}Delete selected ({chosen.length})</button>
      {rows.some(row=>row.locked)&&<small>Clips in processing projects can be deleted after processing finishes.</small>}
    </section>}
    {deleting&&<p className="clip-delete-feedback" role="status">Deleting clips… {completed} / {total}. Please wait.</p>}
    {feedback&&<div className="clip-delete-feedback" role="status"><p>{feedback.message}</p>{feedback.errors.length>0&&<ul>{feedback.errors.map((error,index)=><li key={index}>{error}</li>)}</ul>}</div>}
    <div className="clip-list">{rows.map(row=><article className="library-clip" key={row.key} data-clip-id={row.clip.id} aria-label={`${row.clip.title} from ${row.project.name}`}>
      <input className="clip-row-select" type="checkbox" aria-label={`Select clip ${row.clip.title}`} checked={selected.has(row.key)&&!row.locked} disabled={deleting||row.locked} onChange={event=>{const checked=event.target.checked;setSelected(previous=>{const next=new Set(previous);if(checked)next.add(row.key);else next.delete(row.key);return next;});}}/>
      <div className="clip-icon"><Film size={20}/></div>
      <div className="clip-library-details"><strong>{row.clip.title}</strong><small>{row.project.name} · {time(row.clip.end-row.clip.start)} · {row.clip.status}</small>{row.locked&&<small>Delete available after processing finishes</small>}</div>
      <div className="clip-library-actions"><button type="button" className="secondary" disabled={deleting} onClick={()=>onOpen(row.project.id,row.clip.id)}>Open editor<ArrowRight size={14}/></button>
        {row.clip.status==='ready'&&<a className="icon-button" href={`/api/projects/${row.project.id}/media/${row.clip.id}${row.clip.file?'?v='+encodeURIComponent(row.clip.file):''}`} download aria-label={`Download ${row.clip.title}`}><ArrowDownToLine size={17}/></a>}
        <button type="button" className="clip-delete-button" aria-label={`Delete clip ${row.clip.title}`} disabled={deleting||row.locked} onClick={()=>void remove([row])}><Trash2 size={15}/>Delete</button>
      </div>
    </article>)}</div>
    {!rows.length&&query&&<p className="muted">No clips match your search.</p>}
  </div>;
}
