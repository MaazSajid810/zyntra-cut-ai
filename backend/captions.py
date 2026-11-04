"""Word-timed ASS events. Unaligned/edited text uses labelled phrase fallback."""
import re


def aligned(segment):
    items=segment.get('words') or []
    return bool(items) and re.sub(r'\s+','', ''.join(w['word'] for w in items))==re.sub(r'\s+','',segment['text']) and all(segment['start']-.05<=w['start']<w['end']<=segment['end']+.05 for w in items)


def events(segments,start,end,speed,mode,animation,highlight,literal,stamp,neon_highlight=False):
    for segment in segments:
        if not aligned(segment):continue
        words=segment['words']
        for offset in range(0,len(words),5):
            group=words[offset:offset+5]
            for index,word in enumerate(group):
                a,b=max(start,word['start']),min(end,word['end'])
                if b<=a:continue
                duration=max(1,round((b-a)/speed*1000))
                anim={
                    'none':'',
                    'fade':r'{\fad(50,50)}',
                    'pop':r'{\fscx88\fscy88\t(0,90,\fscx100\fscy100)}',
                    'bounce':r'{\fscx90\fscy90\t(0,65,\fscx108\fscy108)\t(65,140,\fscx100\fscy100)}',
                    'scale':r'{\fscx95\fscy95\t(0,'+str(duration)+r',\fscx105\fscy105)}',
                }[animation]
                active=r'{\1c'+highlight+r'&'+(r'\3c'+highlight+r'&\bord3\blur0.6' if neon_highlight else '')+'}'
                if mode=='word':
                    text=(active if neon_highlight else '')+literal(word['word'].strip())
                else:
                    parts=[]
                    for i,w in enumerate(group):
                        text=literal(w['word'].strip())
                        if i==index:text=active+text+r'{\rDefault}'
                        parts.append(text)
                    text=' '.join(parts)
                yield f'Dialogue: 0,{stamp((a-start)/speed)},{stamp((b-start)/speed)},Default,,0,0,0,,{anim}{text}\n'
