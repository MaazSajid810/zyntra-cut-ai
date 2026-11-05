'use client';
import {useEffect,useState} from 'react';
import SubtitleOptions,{CaptionScript,SpeechLanguage} from './SubtitleOptions';
export default function TranscriptLanguageControls({script='original',language='auto',disabled,onConvert,onTranscribe}:{script?:CaptionScript;language?:SpeechLanguage;disabled:boolean;onConvert:(script:CaptionScript)=>Promise<void>;onTranscribe:(script:CaptionScript,language:SpeechLanguage)=>Promise<void>}){
  const [chosen,setChosen]=useState(script);
  const [spoken,setSpoken]=useState(language);
  useEffect(()=>setChosen(script),[script]);
  useEffect(()=>setSpoken(language),[language]);
  return <div className="transcript-language-controls"><SubtitleOptions prefix="Transcript " script={chosen} language={spoken} onScript={setChosen} onLanguage={setSpoken} disabled={disabled}/>
    <div className="transcript-language-actions"><button type="button" className="secondary" disabled={disabled||chosen===script} onClick={()=>{if(window.confirm(['hindi','urdu','english','roman_urdu'].includes(chosen)?'Generate the selected subtitle language? If compatible saved text is unavailable, audio is transcribed again and edited text is replaced. Clip ranges stay intact; exports become drafts.':'Change the saved subtitle script? Existing clips keep their ranges but exports become drafts and need rendering.'))void onConvert(chosen);}}>Apply subtitle script</button>
    <button type="button" className="secondary" disabled={disabled} onClick={()=>{if(window.confirm('Re-transcribe the source audio using the current speech model? This replaces edited transcript text and marks existing exports as drafts; clip ranges stay intact.'))void onTranscribe(chosen,spoken);}}>Re-transcribe audio</button></div>
    <small>Original keeps the detected native language. Urdu/Hindi speech can also use Roman Urdu. Cross-language captions require an installed translation model; unavailable pairs keep original captions with a notice. Use Translate captions + voice below for offline dubbing. Language changes can replace edited text; Original restores saved source text when available.</small>
  </div>;
}
