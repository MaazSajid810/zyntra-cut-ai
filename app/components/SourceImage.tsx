'use client';
import {useEffect,useState} from 'react';
import {Video} from 'lucide-react';

export default function SourceImage({src,alt='',youtubeId}:{src?:string|null;alt?:string;youtubeId?:string}){
 const url=youtubeId&&/^[A-Za-z0-9_-]{11}$/.test(youtubeId)?`/api/discover/${youtubeId}/thumbnail`:src;
 const [failed,setFailed]=useState(false);
 useEffect(()=>setFailed(false),[url]);
 return url&&!failed?<img src={url} alt={alt} loading="lazy" onError={()=>setFailed(true)}/>:<div className="source-image-fallback" role="img" aria-label="Thumbnail unavailable"><Video size={32}/><small>Thumbnail unavailable</small></div>;
}
