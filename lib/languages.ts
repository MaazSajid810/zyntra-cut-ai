/** Language tokens supported by the bundled multilingual Whisper runtime. */
export const SPEECH_LANGUAGES = [
  ['auto','Detect automatically'],['ur','Urdu'],['hi','Hindi'],['pa','Punjabi'],
  ['ps','Pashto'],['sd','Sindhi'],['en','English'],['es','Spanish'],
  ['af','Afrikaans'],['sq','Albanian'],['am','Amharic'],['ar','Arabic'],
  ['hy','Armenian'],['as','Assamese'],['az','Azerbaijani'],['ba','Bashkir'],
  ['eu','Basque'],['be','Belarusian'],['bn','Bengali'],['bs','Bosnian'],
  ['br','Breton'],['bg','Bulgarian'],['my','Burmese'],['yue','Cantonese'],
  ['ca','Catalan'],['zh','Chinese'],['hr','Croatian'],['cs','Czech'],
  ['da','Danish'],['nl','Dutch'],['et','Estonian'],['fo','Faroese'],
  ['fi','Finnish'],['fr','French'],['gl','Galician'],['ka','Georgian'],
  ['de','German'],['el','Greek'],['gu','Gujarati'],['ht','Haitian Creole'],
  ['ha','Hausa'],['haw','Hawaiian'],['he','Hebrew'],['hu','Hungarian'],
  ['is','Icelandic'],['id','Indonesian'],['it','Italian'],['ja','Japanese'],
  ['jw','Javanese'],['kn','Kannada'],['kk','Kazakh'],['km','Khmer'],
  ['ko','Korean'],['lo','Lao'],['la','Latin'],['lv','Latvian'],
  ['ln','Lingala'],['lt','Lithuanian'],['lb','Luxembourgish'],['mk','Macedonian'],
  ['mg','Malagasy'],['ms','Malay'],['ml','Malayalam'],['mt','Maltese'],
  ['mi','Maori'],['mr','Marathi'],['mn','Mongolian'],['ne','Nepali'],
  ['no','Norwegian'],['nn','Norwegian Nynorsk'],['oc','Occitan'],['fa','Persian'],
  ['pl','Polish'],['pt','Portuguese'],['ro','Romanian'],['ru','Russian'],
  ['sa','Sanskrit'],['sr','Serbian'],['sn','Shona'],['si','Sinhala'],
  ['sk','Slovak'],['sl','Slovenian'],['so','Somali'],['su','Sundanese'],
  ['sw','Swahili'],['sv','Swedish'],['tl','Tagalog'],['tg','Tajik'],
  ['ta','Tamil'],['tt','Tatar'],['te','Telugu'],['th','Thai'],
  ['bo','Tibetan'],['tr','Turkish'],['tk','Turkmen'],['uk','Ukrainian'],
  ['uz','Uzbek'],['vi','Vietnamese'],['cy','Welsh'],['yi','Yiddish'],['yo','Yoruba'],
] as const;

export type SpeechLanguage = typeof SPEECH_LANGUAGES[number][0];

/** Explicit caption targets; Original also preserves any other detected language. */
export const CAPTION_LANGUAGES = [
  ['original','Original / no translation'],['roman_urdu','Roman Urdu'],
  ['urdu','Urdu'],['hindi','Hindi'],['english','English'],
  ['punjabi','Punjabi'],['pashto','Pashto'],['sindhi','Sindhi'],
  ['spanish','Spanish'],['french','French'],['arabic','Arabic'],
  ['bengali','Bengali'],['german','German'],['portuguese','Portuguese'],['italian','Italian'],
] as const;

export type CaptionScript = typeof CAPTION_LANGUAGES[number][0];
export const CAPTION_TARGET_CODES:Partial<Record<CaptionScript,SpeechLanguage>> = {
  roman_urdu:'ur',urdu:'ur',hindi:'hi',english:'en',punjabi:'pa',pashto:'ps',sindhi:'sd',
  spanish:'es',french:'fr',arabic:'ar',bengali:'bn',german:'de',portuguese:'pt',italian:'it',
};

export function speechLabel(code:string):string {
  return SPEECH_LANGUAGES.find(([value])=>value===code)?.[1] || code;
}
