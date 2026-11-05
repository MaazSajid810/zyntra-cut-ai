'use client';
import {useEffect,useState} from 'react';
import {guestFetch,decodeApiResponse} from './api';
import {CAPTION_TARGET_CODES,speechLabel,type CaptionScript,type SpeechLanguage} from './languages';

export type LanguageCapabilities = {
  speech_languages:{code:string;name:string}[];
  caption_languages:{script:string;language:string|null;name:string;translation_available:boolean}[];
  translation_pairs:{source:string;target:string;installed:boolean}[];
};

export default function useLanguageCapabilities(){
  const [capabilities,setCapabilities]=useState<LanguageCapabilities|null>(null);
  useEffect(()=>{
    let current=true;
    void guestFetch('/api/languages').then(async response=>{
      const data=decodeApiResponse<LanguageCapabilities>(await response.text(),response.status);
      if(current)setCapabilities(data);
    }).catch(()=>{/* Existing offline/local workflows remain usable without discovery. */});
    return()=>{current=false;};
  },[]);
  return capabilities;
}

export function captionOptionLabel(script:CaptionScript,label:string,capabilities:LanguageCapabilities|null){
  if(script==='original'||!capabilities)return label;
  const capability=capabilities.caption_languages.find(item=>item.script===script);
  return capability?.translation_available?`${label} · native / translate`:`${label} · native captions`;
}

function hasRoute(source:string,target:string,capabilities:LanguageCapabilities){
  const visited=new Set([source]),queue=[source];
  while(queue.length){
    const next=queue.shift()!;
    if(next===target)return true;
    for(const pair of capabilities.translation_pairs){
      if(pair.installed&&pair.source===next&&!visited.has(pair.target)){
        visited.add(pair.target);queue.push(pair.target);
      }
    }
  }
  return false;
}

export function languageGuidance(script:CaptionScript,source:SpeechLanguage,capabilities:LanguageCapabilities|null){
  if(script==='original')return 'Original captions keep the recognized speech. No translation or voice replacement.';
  const target=CAPTION_TARGET_CODES[script];
  if(source===target||script==='roman_urdu'&&['ur','hi'].includes(source))return 'The selected output uses the recognized speech in its native script or Roman Urdu. Review spelling and names.';
  if(source==='auto'||!target||!capabilities)return 'The spoken language is detected independently. Translation requires an installed local model; an unavailable language pair keeps original captions and displays a notice.';
  if(hasRoute(source,target,capabilities))return `Local ${speechLabel(source)} → ${speechLabel(target)} caption translation is available. This changes subtitles, not the speaker's voice; review the translated meaning.`;
  return `${speechLabel(source)} → ${speechLabel(target)} translation is not installed. Native captions are available when the speech matches the selected language; otherwise the app keeps original captions and displays a notice.`;
}
