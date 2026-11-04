'use client';
import {useRef,type ReactNode,type PointerEvent,type KeyboardEvent} from 'react';
import {type EffectSettings} from '../../lib/editor';

type Props={projectId:string;ratio:number;length:number;effects:EffectSettings;photo?:{id:string;width?:number;height?:number};disabled:boolean;onChange:(patch:Partial<EffectSettings>)=>void;children:ReactNode};
export default function PhotoLayerPanel({projectId,ratio,length,effects:e,photo,disabled,onChange,children}:Props){
  const stage=useRef<HTMLDivElement>(null);
  const drag=useRef<{px:number;py:number;x:number;y:number;freeX:number;freeY:number}|null>(null);
  const clamp=(n:number)=>Math.max(0,Math.min(100,n));
  function position(x:number,y:number){onChange({image_x:clamp(x),image_y:clamp(y)});}
  function begin(event:PointerEvent<HTMLButtonElement>){
    if(disabled||!stage.current)return;
    event.preventDefault();const parent=stage.current.getBoundingClientRect(),item=event.currentTarget.getBoundingClientRect();
    drag.current={px:event.clientX,py:event.clientY,x:e.image_x,y:e.image_y,freeX:Math.max(1,parent.width-item.width),freeY:Math.max(1,parent.height-item.height)};
    event.currentTarget.setPointerCapture(event.pointerId);
  }
  function move(event:PointerEvent<HTMLButtonElement>){const d=drag.current;if(d)position(d.x+(event.clientX-d.px)/d.freeX*100,d.y+(event.clientY-d.py)/d.freeY*100);}
  function keys(event:KeyboardEvent<HTMLButtonElement>){
    if(disabled||!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(event.key))return;
    event.preventDefault();const step=event.shiftKey?10:1;
    position(e.image_x+(event.key==='ArrowLeft'?-step:event.key==='ArrowRight'?step:0),e.image_y+(event.key==='ArrowUp'?-step:event.key==='ArrowDown'?step:0));
  }
  const photoRatio=(photo?.width||1)/(photo?.height||1);
  const width=Math.min(e.image_width,90*photoRatio/ratio);
  return <fieldset data-tool-category="layers" className="studio-layer-panel" disabled={disabled}>
    <legend>Photo / image overlay</legend>
    <p>Add your own PNG, JPEG or WebP as a photo overlay or a full-frame cutaway. Source audio continues and captions stay above the image.</p>
    {children}
    <div className="layer-controls">
      <label>Photo starts (output seconds)<input aria-label="Photo start" type="number" min="0" max={length} step=".1" value={e.image_start} onChange={event=>onChange({image_start:Number(event.target.value)})}/></label>
      <label>Photo ends (output seconds)<input aria-label="Photo end" type="number" min=".01" max="600" step=".01" value={e.image_end} onChange={event=>onChange({image_end:Number(event.target.value)})}/></label>
      <label>Photo layout<select aria-label="Photo layout" value={e.image_layout} onChange={event=>onChange({image_layout:event.target.value as EffectSettings['image_layout']})}><option value="overlay">Movable photo overlay</option><option value="full">Full-frame photo cutaway</option></select></label>
      <label>Photo opacity ({Math.round(e.image_opacity*100)}%)<input aria-label="Photo opacity" type="range" min="0" max="1" step=".01" value={e.image_opacity} onChange={event=>onChange({image_opacity:Number(event.target.value)})}/></label>
      {e.image_layout==='full'?<label>Photo fit<select aria-label="Photo fit" value={e.image_fit} onChange={event=>onChange({image_fit:event.target.value as EffectSettings['image_fit']})}><option value="contain">Show whole photo with padding</option><option value="cover">Fill frame with cropping</option></select></label>:<label>Photo width ({e.image_width}%)<input aria-label="Photo width" type="range" min="3" max="100" value={e.image_width} onChange={event=>onChange({image_width:Number(event.target.value)})}/></label>}
    </div>
    {photo&&<>
      <div className="branding-stage" ref={stage} style={{aspectRatio:ratio}} aria-label="Photo placement guide">
        <img alt="Source frame for photo placement" src={`/api/projects/${projectId}/media/poster`} style={{objectFit:e.framing==='crop'?'cover':'contain',objectPosition:`${e.crop_x}% ${e.crop_y}%`}}/>
        {e.image_layout==='full'?<img className="photo-full-guide" alt="Full-frame photo guide" src={`/api/projects/${projectId}/assets/${photo.id}`} style={{objectFit:e.image_fit,opacity:e.image_opacity,background:'#000'}}/>:<button type="button" className="branding-handle logo" aria-label="Drag photo overlay" onPointerDown={begin} onPointerMove={move} onPointerUp={()=>{drag.current=null;}} onPointerCancel={()=>{drag.current=null;}} onKeyDown={keys} style={{left:`${e.image_x}%`,top:`${e.image_y}%`,transform:`translate(-${e.image_x}%,-${e.image_y}%)`,width:`${width}%`}}><img draggable={false} alt="Your photo overlay" src={`/api/projects/${projectId}/assets/${photo.id}`} style={{opacity:e.image_opacity}}/></button>}
      </div>
      {e.image_layout==='overlay'&&<div className="layer-controls">{(['x','y'] as const).map(axis=><label key={axis}>Photo {axis.toUpperCase()}<input aria-label={`Photo ${axis.toUpperCase()}`} type="range" min="0" max="100" step=".1" value={e[`image_${axis}`]} onChange={event=>onChange({[`image_${axis}`]:Number(event.target.value)})}/></label>)}</div>}
    </>}
    <small>Drag the photo, use arrow keys (Shift for larger moves), or use the position sliders. Times follow the final playback speed; end is limited to output length. This is a placement guide. Apply & render updates the actual video preview and download.</small>
  </fieldset>;
}
