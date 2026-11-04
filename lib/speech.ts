import type {CaptionScript,SpeechLanguage} from './languages';
export type TranscriptionMode='fast'|'quick'|'balanced'|'accurate';

export function recognitionChoices(script:CaptionScript,language:SpeechLanguage):[TranscriptionMode,string][] {
  const small=(!['original','roman_urdu'].includes(script))||['pa','ps','sd'].includes(language)||script==='roman_urdu'&&language!=='en';
  return [
    ['quick',`Quick · batched ${small?'small':'base'} model`],
    ['balanced',`Balanced · ${small?'small':'base'} model · context`],
    ['accurate',`Accurate · ${small?'small':'base'} model · slower`],
    ['fast',small?'Fast · batched small model':'Fast · tiny model · lower accuracy'],
  ];
}
