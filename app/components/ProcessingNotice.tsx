'use client';
import {useEffect,useState,type ReactNode} from 'react';
import {createPortal} from 'react-dom';
import {LoaderCircle,X,AlertCircle} from 'lucide-react';

function FloatingStatus({children}:{children:ReactNode}){
  const [mounted,setMounted]=useState(false);
  useEffect(()=>setMounted(true),[]);
  return mounted?createPortal(children,document.body):null;
}

export function ProcessingReopen({onShow}:{onShow:()=>void}){
  return <FloatingStatus><button type="button" className="processing-reopen" onClick={onShow}><LoaderCircle className="spin" size={15}/>Show processing status</button></FloatingStatus>;
}

export default function ProcessingNotice({title,message,progress,details,failed=false,onDismiss}:{title:string;message:string;progress?:number|null;details?:string;failed?:boolean;onDismiss:()=>void}){
  return <FloatingStatus><aside className={`processing-notice ${failed?'failed':''}`} role="region" aria-label="Video processing status" aria-live="polite" aria-busy={!failed}>
    <div className="processing-notice-heading">{failed?<AlertCircle size={20}/>:<LoaderCircle size={20} className="spin"/>}<strong>{title}</strong><button type="button" aria-label="Hide processing status" onClick={onDismiss}><X size={17}/></button></div>
    <p>{message}</p>
    {!failed&&<progress aria-label="Current processing stage" value={typeof progress==='number'?progress:undefined} max={100}/>}
    {details&&<small>{details}</small>}
    {!failed&&<small>Please wait · Processing chal rahi hai. Ready hone par preview dekhein; download aapke click par hoga.</small>}
  </aside></FloatingStatus>;
}
