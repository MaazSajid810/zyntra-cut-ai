'use client';
import {useEffect,useRef,useState,type PointerEvent,type KeyboardEvent} from 'react';
import {decodeApiResponse,guestFetch} from '../../lib/api';
import {type EffectSettings} from '../../lib/editor';
import PhotoLayerPanel from './PhotoLayerPanel';

type Asset={id:string;kind:'logo'|'filler'|'music'|'image';name:string;width?:number;height?:number;duration?:number};
type Limits=Record<Asset['kind'],{max_bytes:number;label:string}>;
type Props={projectId:string;length:number;effects:EffectSettings;disabled:boolean;onChange:(value:Partial<EffectSettings>)=>void;onBusyChange?:(busy:boolean)=>void};
export default function StudioLayers({projectId,length,effects:e,disabled,onChange,onBusyChange}:Props){
  const [assets,setAssets]=useState<Asset[]>([]);
  const [uploading,setUploading]=useState('');
  const [errors,setErrors]=useState<Record<string,string>>({});
  const [limits,setLimits]=useState<Limits|null>(null);
  const [stageWidth,setStageWidth]=useState(400);
  const [sourceRatio,setSourceRatio]=useState(16/9);
  const stage=useRef<HTMLDivElement>(null);
  const drag=useRef<{kind:'text'|'logo';px:number;py:number;x:number;y:number;freeX:number;freeY:number}|null>(null);
  useEffect(()=>{let alive=true;void Promise.all([guestFetch(`/api/projects/${projectId}/assets`).then(async response=>decodeApiResponse<Asset[]>(await response.text(),response.status)),guestFetch('/api/assets/limits').then(async response=>decodeApiResponse<Limits>(await response.text(),response.status))]).then(([data,policy])=>{if(alive){setAssets(data);setLimits(policy);}}).catch(err=>{if(alive)setErrors({general:String(err)});});return()=>{alive=false;};},[projectId]);
  useEffect(()=>{if(!stage.current)return;const observer=new ResizeObserver(entries=>setStageWidth(entries[0].contentRect.width));observer.observe(stage.current);return()=>observer.disconnect();},[]);
  async function upload(kind:Asset['kind'],file?:File){
    if(!file||uploading||disabled||!limits)return;
    const policy=limits[kind];setErrors(previous=>({...previous,[kind]:''}));
    if(!file.size){setErrors(previous=>({...previous,[kind]:'Choose a non-empty file.'}));return;}
    if(file.size>policy.max_bytes){setErrors(previous=>({...previous,[kind]:`${policy.label} is ${(file.size/1024**2).toFixed(1)} MB. Maximum: ${policy.max_bytes/1024**2} MB. Choose a smaller file; this file was not uploaded.`}));return;}
    setUploading(kind);onBusyChange?.(true);
    try{
      const form=new FormData();form.append('file',file);
      const response=await guestFetch(`/api/projects/${projectId}/assets?kind=${kind}`,{method:'POST',body:form});
      const asset=decodeApiResponse<Asset>(await response.text(),response.status);
      setAssets(previous=>[...previous,asset]);
      if(kind==='logo')onChange({logo_asset_id:asset.id});
      if(kind==='filler')onChange({filler_asset_id:asset.id,filler_start:0,filler_end:Math.min(3,length)});
      if(kind==='music')onChange({music_asset_id:asset.id});
      if(kind==='image')onChange({image_asset_id:asset.id,image_start:0,image_end:Math.min(3,length)});
    }catch(err){setErrors(previous=>({...previous,[kind]:err instanceof Error?err.message:'Asset upload failed.'}));}
    finally{setUploading('');onBusyChange?.(false);}
  }
  function picker(kind:Asset['kind'],label:string,selected:string|null){
    const image=kind==='logo'||kind==='image';
    const title=limits?.[kind].label||label;
    return <div className="asset-picker"><label>{label}<select aria-label={label} disabled={disabled||!!uploading} value={selected||''} onChange={event=>onChange({[`${kind}_asset_id`]:event.target.value||null})}><option value="">None</option>{assets.filter(asset=>asset.kind===kind).map(asset=><option key={asset.id} value={asset.id}>{asset.name}</option>)}</select></label><label>Upload {title.toLowerCase()}<input aria-label={`Upload ${kind}`} type="file" accept={image?'image/png,image/jpeg,image/webp':kind==='filler'?'video/*':'audio/*'} disabled={disabled||!!uploading||!limits} onChange={event=>{void upload(kind,event.target.files?.[0]);event.target.value='';}}/><small>{limits?`Maximum ${limits[kind].max_bytes/1024**2} MB`:'Loading upload limits...'}{image?' | PNG, JPEG, WebP | up to 4096 px':''}</small></label>{uploading===kind&&<p role="status">Uploading and validating {title.toLowerCase()}...</p>}{errors[kind]&&<div role="alert" className="asset-error"><p>{errors[kind]}</p><button className="text-button" type="button" aria-label={`Dismiss ${kind} upload error`} onClick={()=>setErrors(previous=>({...previous,[kind]:''}))}>Dismiss</button></div>}</div>;
  }
  const logo=assets.find(asset=>asset.id===e.logo_asset_id);
  const ratio=e.aspect==='vertical'?9/16:e.aspect==='square'?1:e.aspect==='portrait'?4/5:e.aspect==='landscape'?16/9:sourceRatio;
  const logoRatio=(logo?.width||1)/(logo?.height||1);
  const logoWidth=Math.min(e.logo_width,60*logoRatio/ratio);
  function position(kind:'text'|'logo',x:number,y:number){
    const clamp=(value:number)=>Math.max(0,Math.min(100,value));
    onChange(kind==='text'?{watermark_x:clamp(x),watermark_y:clamp(y)}:{logo_x:clamp(x),logo_y:clamp(y)});
  }
  function begin(event:PointerEvent<HTMLButtonElement>,kind:'text'|'logo'){
    if(disabled||!stage.current)return;
    event.preventDefault();
    const parent=stage.current.getBoundingClientRect(),item=event.currentTarget.getBoundingClientRect();
    drag.current={kind,px:event.clientX,py:event.clientY,x:kind==='text'?e.watermark_x:e.logo_x,y:kind==='text'?e.watermark_y:e.logo_y,freeX:Math.max(1,parent.width-item.width),freeY:Math.max(1,parent.height-item.height)};
    event.currentTarget.setPointerCapture(event.pointerId);
  }
  function move(event:PointerEvent<HTMLButtonElement>){const d=drag.current;if(d)position(d.kind,d.x+(event.clientX-d.px)/d.freeX*100,d.y+(event.clientY-d.py)/d.freeY*100);}
  function keys(event:KeyboardEvent<HTMLButtonElement>,kind:'text'|'logo'){
    if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(event.key)||disabled)return;
    event.preventDefault();const step=event.shiftKey?10:1;
    position(kind,(kind==='text'?e.watermark_x:e.logo_x)+(event.key==='ArrowLeft'?-step:event.key==='ArrowRight'?step:0),(kind==='text'?e.watermark_y:e.logo_y)+(event.key==='ArrowUp'?-step:event.key==='ArrowDown'?step:0));
  }
  const dragProps=(kind:'text'|'logo')=>({onPointerDown:(event:PointerEvent<HTMLButtonElement>)=>begin(event,kind),onPointerMove:move,onPointerUp:()=>{drag.current=null;},onPointerCancel:()=>{drag.current=null;},onKeyDown:(event:KeyboardEvent<HTMLButtonElement>)=>keys(event,kind)});
  return <>
    {errors.general&&<p role="alert" className="asset-error">{errors.general}</p>}
    <fieldset data-tool-category="branding" className="studio-layer-panel" disabled={disabled}>
      <legend>Channel branding</legend><p>Only your own enabled text/logo is added. Drag either item, use arrow keys, or set its X/Y sliders. Apply & render creates the final preview.</p>
      <label className="check-field"><input type="checkbox" checked={e.watermark_enabled} onChange={event=>onChange({watermark_enabled:event.target.checked})}/>Enable text watermark</label>
      <label>Channel name / watermark text<input aria-label="Watermark text" maxLength={120} value={e.watermark_text} onChange={event=>onChange({watermark_text:event.target.value})}/></label>
      <div className="layer-controls"><label>Text opacity ({Math.round(e.watermark_opacity*100)}%)<input aria-label="Watermark opacity" type="range" min="0" max="1" step=".01" value={e.watermark_opacity} onChange={event=>onChange({watermark_opacity:Number(event.target.value)})}/></label><label>Text size<input aria-label="Watermark size" type="number" min="18" max="180" value={e.watermark_size} onChange={event=>onChange({watermark_size:Number(event.target.value)})}/></label><label>Watermark color<input aria-label="Watermark color" type="color" value={e.watermark_color} onChange={event=>onChange({watermark_color:event.target.value})}/></label></div>
      {picker('logo','Channel logo',e.logo_asset_id)}
      <div className="layer-controls"><label>Logo opacity ({Math.round(e.logo_opacity*100)}%)<input aria-label="Logo opacity" type="range" min="0" max="1" step=".01" value={e.logo_opacity} onChange={event=>onChange({logo_opacity:Number(event.target.value)})}/></label><label>Logo width ({e.logo_width}%)<input aria-label="Logo width" type="range" min="3" max="60" value={e.logo_width} onChange={event=>onChange({logo_width:Number(event.target.value)})}/></label></div>
      <div className="branding-stage" ref={stage} style={{aspectRatio:ratio}} aria-label="Watermark placement guide">
        <img alt="Source frame for placement" src={`/api/projects/${projectId}/media/poster`} style={{objectFit:e.framing==='crop'?'cover':'contain',objectPosition:`${e.crop_x}% ${e.crop_y}%`}} onLoad={event=>{const image=event.currentTarget;setSourceRatio(image.naturalWidth/image.naturalHeight);}}/>
        {e.watermark_enabled&&e.watermark_text&&<button type="button" className="branding-handle text" aria-label="Drag text watermark" {...dragProps('text')} style={{left:`${e.watermark_x}%`,top:`${e.watermark_y}%`,transform:`translate(-${e.watermark_x}%,-${e.watermark_y}%)`,fontSize:Math.max(8,e.watermark_size*stageWidth/720),color:e.watermark_color}}><span style={{opacity:e.watermark_opacity}}>{e.watermark_text}</span></button>}
        {logo&&<button type="button" className="branding-handle logo" aria-label="Drag channel logo" {...dragProps('logo')} style={{left:`${e.logo_x}%`,top:`${e.logo_y}%`,transform:`translate(-${e.logo_x}%,-${e.logo_y}%)`,width:`${logoWidth}%`}}><img alt="Your channel logo" draggable={false} src={`/api/projects/${projectId}/assets/${logo.id}`} style={{opacity:e.logo_opacity}}/></button>}
      </div>
      <small>Placement guide uses a source frame. Final filters, captions, transparency and movement appear after rendering. PNG transparency is preserved.</small>
      <div className="layer-controls">{(['watermark','logo'] as const).flatMap(kind=>(['x','y'] as const).map(axis=><label key={kind+axis}>{kind==='watermark'?'Text':'Logo'} {axis.toUpperCase()}<input aria-label={`${kind==='watermark'?'Watermark':'Logo'} ${axis.toUpperCase()}`} type="range" min="0" max="100" step=".1" value={e[`${kind}_${axis}`]} onChange={event=>onChange({[`${kind}_${axis}`]:Number(event.target.value)})}/></label>))}</div>
    </fieldset>
    <fieldset data-tool-category="layers" className="studio-layer-panel" disabled={disabled}><legend>Filler video / B-roll</legend><p>Upload your own cutaway, gameplay or supporting video. It overlays the source during your chosen output-time range; source speech continues and captions stay on top. Short B-roll loops to fill the range.</p>
      {picker('filler','B-roll video',e.filler_asset_id)}<div className="layer-controls"><label>B-roll starts (output seconds)<input aria-label="B-roll start" type="number" min="0" max={length} step=".1" value={e.filler_start} onChange={event=>onChange({filler_start:Number(event.target.value)})}/></label><label>B-roll ends (output seconds)<input aria-label="B-roll end" type="number" min="0.01" max="600" step=".01" value={e.filler_end} onChange={event=>onChange({filler_end:Number(event.target.value)})}/></label><label>B-roll layout<select aria-label="B-roll layout" value={e.filler_layout} onChange={event=>onChange({filler_layout:event.target.value as EffectSettings['filler_layout']})}><option value="full">Full-frame cutaway</option><option value="pip">Picture in picture</option></select></label></div><small>Times follow final playback speed. End is limited to the output length. Choose Fade under Effects for a dissolve at B-roll entry/exit.</small>
    </fieldset>
    <PhotoLayerPanel projectId={projectId} ratio={ratio} length={length} effects={e} photo={assets.find(asset=>asset.id===e.image_asset_id)} disabled={disabled} onChange={onChange}>{picker('image','Photo',e.image_asset_id)}</PhotoLayerPanel>
    <fieldset data-tool-category="audio" className="studio-layer-panel" disabled={disabled}><legend>Music and sound effects</legend>
      {picker('music','Background music',e.music_asset_id)}<label>Music volume ({Math.round(e.music_volume*100)}%)<input aria-label="Music volume" type="range" min="0" max="1" step=".01" value={e.music_volume} onChange={event=>onChange({music_volume:Number(event.target.value)})}/></label>
      <div className="layer-controls"><label>Sound effect<select aria-label="Sound effect" value={e.sound_effect} onChange={event=>onChange({sound_effect:event.target.value as EffectSettings['sound_effect']})}>{[['none','None'],['pop','Pop'],['ding','Ding'],['whoosh','Whoosh']].map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label><label>Sound starts (output seconds)<input aria-label="Sound starts" type="number" min="0" max={length} step=".1" value={e.sound_at} onChange={event=>onChange({sound_at:Number(event.target.value)})}/></label><label>Sound volume ({Math.round(e.sound_volume*100)}%)<input aria-label="Sound volume" type="range" min="0" max="1" step=".01" value={e.sound_volume} onChange={event=>onChange({sound_volume:Number(event.target.value)})}/></label></div><p>Sound effects are original synthesized audio. Uploaded music loops with an ending fade. Source Mute silences the original voice; added music/effects keep their own volume. Render and listen before downloading.</p>
    </fieldset>
  </>;
}
