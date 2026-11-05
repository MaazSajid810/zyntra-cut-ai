'use client';

import {useEffect,useState} from 'react';

const content = {
  en: {
    title:'New here? Make your first clip.',
    intro:'Start with a short test video, then try a longer project.',
    steps:[
      ['Add your video','Choose Upload video, or open Link to clips in the sidebar: paste a public video/reel link from a supported platform or a direct video URL and choose Get clips. Private or blocked links may fail; upload the file instead.'],
      ['Choose your clips','Set Number of clips (1–100) and a transcription mode. Generate new clips creates speech-based highlights; short videos may produce fewer clips. You can also create a manual clip.'],
      ['Review your captions','Choose Subtitle script: Roman Urdu to write Urdu/Hindi speech in English letters; English remains English. Use Balanced/Accurate and select the spoken language if detection is wrong. In Transcript, Apply subtitle script converts saved text without another speech run. Correct words/times and Save subtitles; render again to update exports. The first speech run downloads its model.'],
      ['Set the look and speed','Choose 9:16, 1:1 or another format, 480p/720p/1080p, and 1x–4x speed. Pick a subtitle design, font, color, voice/video effect or custom text. Start/end use original-video time.'],
      ['Hide the webcam if needed','Enable Cover creator face / webcam area, choose a corner, then adjust its size/position in the source preview. This adds a fixed black cover. Keep full video avoids cropping; Fill frame lets you adjust the crop.'],
      ['Save, render and download','Save changes, then Render video. After changing a saved clip’s font/filter, Apply & render saves and exports in one click. Selecting Warm/Vintage alone does not update an old export. Apply styling to all drafts and Render all drafts exports a batch. Wait for Ready, preview, then download MP4/WebM.'],
    ],
    tip:'For quicker tests use Fast transcription, Fast 480p MP4, and 1–2 clips. Clip speed changes the finished video; it is separate from processing speed.',
  },
  ur: {
    title:'Pehli baar? Apni pehli clip banayen.',
    intro:'Pehle chhoti test video se shuru karein, phir lamba project try karein.',
    steps:[
      ['Video add karein','Upload video se file chunen. Sidebar mein Link to clips kholen, kisi supported platform ka public video/reel ya direct video link paste karein aur Get clips dabayen. Private ya blocked link na chale to file upload karein.'],
      ['Clips ki tadaad chunen','Number of clips mein 1–100 chunen aur transcription mode set karein. Generate new clips se boli hui baaton par highlights banti hain; chhoti video se kam clips mil sakti hain. Manual clip bhi bana sakte hain.'],
      ['Captions check karein','Subtitle script mein Roman Urdu chunen: Urdu/Hindi ki boli hui baat English letters mein aayegi, English ki translation nahi hogi. Balanced/Accurate behtar hai; detection ghalat ho to Spoken language set karein. Transcript mein Apply subtitle script se saved text convert hota hai. Alfaaz/timing theek karke Save subtitles aur phir render karein. Pehli transcription par model download hota hai.'],
      ['Design aur speed set karein','9:16, 1:1 ya doosra ratio, 480p/720p/1080p aur 1x–4x speed chunen. Subtitle design, font, rang, voice/video effects aur apna text laga sakte hain. Start/end asal video ke seconds hain.'],
      ['Creator ka webcam chhupayen','Cover creator face / webcam area on karein. Corner chun kar source preview mein size aur jagah set karein. Yeh fixed black cover lagata hai. Keep full video mein video nahi katti; Fill frame mein crop adjust hota hai.'],
      ['Save, render aur download karein','Save changes ke baad Render video dabayen. Saved clip ka font/filter badlein to Apply & render se save aur export ek saath hota hai. Sirf Warm/Vintage chunne se purana export nahi badalta. Sab drafts ke liye Apply styling to all drafts aur Render all drafts use karein. Ready hone par preview dekhein aur MP4/WebM download karein.'],
    ],
    tip:'Jaldi test ke liye Fast transcription, Fast 480p MP4 aur 1–2 clips chunen. Clip speed final video ki raftaar hai; processing speed alag cheez hai.',
  },
};

export default function UsageGuide(){
  const [language,setLanguage]=useState<'en'|'ur'>('en');
  useEffect(()=>{try{if(localStorage.getItem('clipforge-guide-language')==='ur')setLanguage('ur');}catch{}},[]);
  function choose(value:'en'|'ur'){
    setLanguage(value);
    try{localStorage.setItem('clipforge-guide-language',value);}catch{}
  }
  const copy=content[language];
  return <section className="usage-guide" aria-label="How to use ZyntraCut AI" lang={language==='ur'?'ur-Latn':'en'}>
    <div className="guide-heading"><div><span className="eyebrow">QUICK START / SHURU KAREIN</span><h2>{copy.title}</h2><p>{copy.intro}</p></div>
      <div className="guide-languages" role="group" aria-label="Guide language"><button type="button" className="secondary" aria-pressed={language==='en'} onClick={()=>choose('en')}>English</button><button type="button" className="secondary" aria-pressed={language==='ur'} onClick={()=>choose('ur')}>Roman Urdu</button></div>
    </div>
    <ol>{copy.steps.map(([title,text])=><li key={title}><strong>{title}</strong><p>{text}</p></li>)}</ol>
    <p className="guide-tip">{copy.tip}</p>
    <p className="guide-tip">{language==='en'?'No login needed: this browser has its own private guest workspace. Keep its cookies to return to your projects. Open a clip to Delete this clip, or use Delete project to remove the whole project and its files. More details are in Setup & workflow.':'Login ki zaroorat nahi: is browser ka apna private guest workspace hai. Projects dobara kholne ke liye cookies na mitayen. Clip khol kar Delete this clip karein; poora project aur files hatane ke liye Delete project use karein. Mazeed maloomat Setup & workflow mein hain.'}</p>
  </section>;
}
