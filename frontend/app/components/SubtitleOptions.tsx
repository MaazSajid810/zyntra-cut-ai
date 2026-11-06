'use client';
import {CAPTION_LANGUAGES,SPEECH_LANGUAGES,type CaptionScript,type SpeechLanguage} from '../../lib/languages';
import useLanguageCapabilities,{captionOptionLabel,languageGuidance} from '../../lib/useLanguageCapabilities';
export type {CaptionScript,SpeechLanguage} from '../../lib/languages';
export default function SubtitleOptions({script,language,onScript,onLanguage,disabled=false,sourceDisabled=false,prefix=''}:{script:CaptionScript;language:SpeechLanguage;onScript:(value:CaptionScript)=>void;onLanguage:(value:SpeechLanguage)=>void;disabled?:boolean;sourceDisabled?:boolean;prefix?:string}){
  const capabilities=useLanguageCapabilities();
  return <div className="subtitle-language-options">
    <label>Subtitle language / script<select aria-label={`${prefix}Subtitle script`} value={script} disabled={disabled} onChange={e=>onScript(e.target.value as CaptionScript)}>{CAPTION_LANGUAGES.map(([value,label])=><option key={value} value={value}>{captionOptionLabel(value,label,capabilities)}</option>)}</select></label>
    <label>Language actually spoken in the video<select aria-label={`${prefix}Spoken language`} value={language} disabled={disabled||sourceDisabled} onChange={e=>onLanguage(e.target.value as SpeechLanguage)}>{SPEECH_LANGUAGES.map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>
    <small>Keep speech detection on Auto unless it is wrong. Choose the language you want in Subtitle language above. This changes captions; use Translate captions + voice in the editor to dub the audio.</small>
    <small role="status">{languageGuidance(script,language,capabilities)}</small>
    <small>Punjabi, Pashto and Sindhi recognition can be less accurate. Review wording, names and script before export. These options change captions. To replace the voice, open Transcript ? Translate captions + voice. Translated captions use sentence timing.</small>
    {sourceDisabled&&script!=='hindi'&&<small>Saved transcript is reused. Change spoken language with Re-transcribe in the Transcript tab.</small>}
  </div>;
}
