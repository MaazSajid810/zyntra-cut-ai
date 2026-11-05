'use client';

import {ArrowDownToLine,ArrowRight,Film,LoaderCircle,Play,Trash2} from 'lucide-react';
import {type Clip} from '../../lib/editor';
import {useState} from 'react';

const time=(s:number)=>`${Math.floor(s/60)}:${Math.floor(s%60).toString().padStart(2,'0')}`;
export default function ClipReview({projectId,clips,selected,onSelect,onEdit,onDelete,onDeleteMany,pending,processing}:{projectId:string;clips:Clip[];selected?:Clip;onSelect:(id:string)=>void;onEdit:(id:string)=>void;onDelete:(id:string)=>void;onDeleteMany:(ids:string[])=>Promise<boolean>;pending:boolean;processing:boolean}){
  const [sort,setSort]=useState('score');
  const [chosen,setChosen]=useState<Set<string>>(new Set());
  const selectedIds=clips.filter(c=>chosen.has(c.id)).map(c=>c.id);
  const ordered=[...clips].sort((a,b)=>sort==='earliest'?a.start-b.start:sort==='duration'?(b.end-b.start)-(a.end-a.start):(b.score??-1)-(a.score??-1)||a.start-b.start);
  const ready=clips.filter(c=>c.status==='ready').length;
  const src=selected?`/api/projects/${projectId}/media/${selected.status==='ready'?selected.id:'source'}${selected.status==='ready'?'?v='+encodeURIComponent(selected.file||''):''}`:'';
  return <section className="clip-review" aria-label="Generated clip previews">
    <header className="review-heading"><div><span className="eyebrow">YOUR SHORTLIST</span><h2>{clips.length} clips to explore</h2><p>{ready} previews ready. Watch first, edit your favorites, then download.</p></div>{processing&&<span role="status"><LoaderCircle size={16} className="spin"/>Preparing remaining previews</span>}</header>
    <div className="review-toolbar" role="group" aria-label="Generated clip actions"><label><input type="checkbox" aria-label="Select all generated clips" checked={clips.length>0&&selectedIds.length===clips.length} disabled={pending||processing} onChange={e=>setChosen(new Set(e.target.checked?clips.map(c=>c.id):[]))}/>Select all</label><span>{selectedIds.length} selected</span><button type="button" disabled={pending||processing||!selectedIds.length} onClick={async()=>{if(await onDeleteMany(selectedIds))setChosen(new Set());}}><Trash2 size={15}/>Delete selected ({selectedIds.length})</button><label>Sort clips<select aria-label="Sort generated clips" value={sort} onChange={e=>setSort(e.target.value)}><option value="score">Highest engagement score</option><option value="earliest">Earliest first</option><option value="duration">Longest first</option></select></label></div>
    <div className="review-layout">
      <div className="review-cards">{ordered.map(c=><article key={c.id} className={`review-card ${selected?.id===c.id?'active':''}`}>
        <label className="review-select"><input type="checkbox" aria-label={`Select generated clip ${c.title}`} checked={chosen.has(c.id)} disabled={pending||processing} onChange={e=>{const checked=e.target.checked;setChosen(prev=>{const next=new Set(prev);if(checked)next.add(c.id);else next.delete(c.id);return next;});}}/>Select clip</label>
        <button type="button" className="review-poster" aria-label={`Preview ${c.title}`} aria-pressed={selected?.id===c.id} onClick={()=>onSelect(c.id)} style={{backgroundImage:`url('/api/projects/${projectId}/media/poster')`}}><Play size={24}/><span>{time(c.end-c.start)}</span></button>
        <button type="button" className="review-title" onClick={()=>onEdit(c.id)}><h3>{c.title}</h3><ArrowRight size={15}/></button>
        <p>{time(c.start)} - {time(c.end)} <span className="status">{c.status}</span></p>
        {c.score!==null&&<small>{c.score}/100 engagement score</small>}
        <div className="review-card-actions"><button type="button" className="secondary" onClick={()=>onEdit(c.id)}>Open editor</button>{c.status==='ready'&&<a className="secondary" href={`/api/projects/${projectId}/media/${c.id}?v=${encodeURIComponent(c.file||'')}`} download aria-label={`Download ${c.title}`}><ArrowDownToLine size={15}/>Download</a>}<button type="button" className="icon-button" aria-label={`Delete ${c.title}`} disabled={pending||processing} onClick={()=>onDelete(c.id)}><Trash2 size={16}/></button></div>
        {c.error&&<p className="error-text">{c.error}</p>}
      </article>)}</div>
      {selected&&<aside role="region" className="review-player" aria-label="Selected clip preview"><div className="panel-heading"><h3><Film size={17}/>{selected.status==='ready'?'Rendered clip preview':'Source range preview'}</h3></div>
        <video key={src+selected.id} src={src} controls playsInline preload="metadata" onPlay={()=>document.querySelectorAll('audio,video').forEach(item=>{if(item instanceof HTMLMediaElement&&item.getAttribute('src')!==src)item.pause();})} onLoadedMetadata={e=>{if(selected.status!=='ready')e.currentTarget.currentTime=selected.start;}} onTimeUpdate={e=>{if(selected.status!=='ready'&&e.currentTarget.currentTime>=selected.end)e.currentTarget.pause();}}/>
        <div className="review-preview-copy"><strong>{selected.title}</strong><p>{selected.status==='ready'?'Final rendered preview with saved captions and effects.':'Source footage only. The final preview becomes available after rendering.'}</p>{selected.reason&&<p>{selected.reason}</p>}
          <button type="button" className="secondary" onClick={()=>onEdit(selected.id)}>Edit this clip<ArrowRight size={15}/></button>
          {selected.status==='ready'&&<a className="primary" href={src} download><ArrowDownToLine size={15}/>Download {selected.file?.endsWith('.webm')?'WebM':'MP4'}</a>}
        </div>
      </aside>}
    </div>
    <p className="filter-hint">Scores help compare candidates; they do not predict guaranteed views. Thumbnails show the original source. Downloads start only when you click.</p>
  </section>;
}
