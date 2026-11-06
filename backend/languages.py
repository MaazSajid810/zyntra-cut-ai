"""Explicit language tokens shared by API validation and local capabilities.

Speech recognition support is separate from installed translation routes.
Native captions never imply that a translation model exists.
"""
from typing import Literal

# These are the 100 multilingual language tokens supported by faster-whisper.
SPEECH_NAMES = {
    'af':'Afrikaans','sq':'Albanian','am':'Amharic','ar':'Arabic','hy':'Armenian',
    'as':'Assamese','az':'Azerbaijani','ba':'Bashkir','eu':'Basque','be':'Belarusian',
    'bn':'Bengali','bs':'Bosnian','br':'Breton','bg':'Bulgarian','my':'Burmese',
    'yue':'Cantonese','ca':'Catalan','zh':'Chinese','hr':'Croatian','cs':'Czech',
    'da':'Danish','nl':'Dutch','en':'English','et':'Estonian','fo':'Faroese',
    'fi':'Finnish','fr':'French','gl':'Galician','ka':'Georgian','de':'German',
    'el':'Greek','es':'Spanish','gu':'Gujarati','ht':'Haitian Creole','ha':'Hausa','haw':'Hawaiian',
    'he':'Hebrew','hi':'Hindi','hu':'Hungarian','is':'Icelandic','id':'Indonesian',
    'it':'Italian','ja':'Japanese','jw':'Javanese','kn':'Kannada','kk':'Kazakh',
    'km':'Khmer','ko':'Korean','lo':'Lao','la':'Latin','lv':'Latvian','ln':'Lingala',
    'lt':'Lithuanian','lb':'Luxembourgish','mk':'Macedonian','mg':'Malagasy',
    'ms':'Malay','ml':'Malayalam','mt':'Maltese','mi':'Maori','mr':'Marathi',
    'mn':'Mongolian','ne':'Nepali','no':'Norwegian','nn':'Norwegian Nynorsk',
    'oc':'Occitan','ps':'Pashto','fa':'Persian','pl':'Polish','pt':'Portuguese',
    'pa':'Punjabi','ro':'Romanian','ru':'Russian','sa':'Sanskrit','sr':'Serbian',
    'sn':'Shona','sd':'Sindhi','si':'Sinhala','sk':'Slovak','sl':'Slovenian',
    'so':'Somali','su':'Sundanese','sw':'Swahili','sv':'Swedish','tl':'Tagalog',
    'tg':'Tajik','ta':'Tamil','tt':'Tatar','te':'Telugu','th':'Thai','bo':'Tibetan',
    'tr':'Turkish','tk':'Turkmen','uk':'Ukrainian','ur':'Urdu','uz':'Uzbek',
    'vi':'Vietnamese','cy':'Welsh','yi':'Yiddish','yo':'Yoruba',
}
SpeechLanguage = Literal['auto', *SPEECH_NAMES]
CAPTION_TARGETS = {
    'roman_urdu':'ur','urdu':'ur','hindi':'hi','english':'en','punjabi':'pa',
    'pashto':'ps','sindhi':'sd','spanish':'es','french':'fr','arabic':'ar',
    'bengali':'bn','german':'de','portuguese':'pt','italian':'it',
}
CaptionScript = Literal['original', *CAPTION_TARGETS]


def caption_name(script):
    if script == 'original':return 'Original / no translation'
    if script == 'roman_urdu':return 'Roman Urdu'
    return SPEECH_NAMES[CAPTION_TARGETS[script]]


def capability_catalog():
    from . import translation
    pairs=[{'source':source,'target':target,'installed':translation.pair_installed(source,target)}
           for source,target in translation.PAIRS]
    if translation.multilingual.installed(translation.ROOT):
        # A star via English is enough for discovery to describe all supported
        # directions; inference itself translates directly between the languages.
        pairs=[{'source':source,'target':target,'installed':True}
               for code in sorted(translation.multilingual.LANGUAGES-{'en'})
               for source,target in (('en',code),(code,'en'))]
    return {
        'speech_languages':[{'code':'auto','name':'Detect automatically'},
                            *({'code':code,'name':name} for code,name in SPEECH_NAMES.items())],
        'caption_languages':[{'script':script,'language':CAPTION_TARGETS.get(script),
                              'name':caption_name(script),
                              'translation_available':script=='original' or any(
                                  translation.route_available(code,CAPTION_TARGETS[script])
                                  for code in SPEECH_NAMES if code!=CAPTION_TARGETS.get(script))}
                             for script in ['original',*CAPTION_TARGETS]],
        'translation_pairs':pairs,
    }
