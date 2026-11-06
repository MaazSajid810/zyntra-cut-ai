'use client';
import SourceImage from './SourceImage';
import {useEffect,useState,useRef} from 'react';
import {ArrowRight,Link2,LoaderCircle,Sparkles,Video} from 'lucide-react';
import {decodeApiResponse,guestFetch,apiErrorMessage} from '../../lib/api';
import {speedOptions,subtitleStyles,subtitleFonts} from '../../lib/editor';
import {recognitionChoices,type TranscriptionMode} from '../../lib/speech';
import SubtitleOptions,{CaptionScript,SpeechLanguage} from './SubtitleOptions';
import ProcessingNotice,{ProcessingReopen} from './ProcessingNotice';
import ClipDuration,{validDuration} from './ClipDuration';
import {CAPTION_LANGUAGES,SPEECH_LANGUAGES} from '../../lib/languages';
import useLanguageCapabilities,{captionOptionLabel,languageGuidance} from '../../lib/useLanguageCapabilities';

type Job={id:string;status:string;progress:number|null;downloaded_bytes:number;message:string;error:string|null;project_id:string|null;options:{url:string};project_progress?:{stage:string;transcription_progress:number;total:number;ready:number}};
type SourcePreview={title:string;duration:number|null;platform:string;thumbnail:string|null;url:string};
const storageKey='clipforge-active-link-import';
const aspectOptions=[['original','Original source ratio'],['vertical','9:16 Shorts / Reels'],['square','1:1 Square'],['landscape','16:9 Landscape'],['portrait','4:5 Portrait']] as const;
export default function LinkImporter({onProject,studio=false,onUpload,initialUrl=''}:{onProject:(id:string)=>Promise<void>;studio?:boolean;onUpload?:()=>void;initialUrl?:string}) {
  const languageCapabilities=useLanguageCapabilities();
  const urlInput=useRef<HTMLInputElement>(null);
  const [platform,setPlatform]=useState('YouTube');
  const [preset,setPreset]=useState('Reels');
  const [aspect,setAspect]=useState('vertical');
  const [framing,setFraming]=useState('follow');
  const [animation,setAnimation]=useState('pop');
  const [url,setUrl]=useState(initialUrl);
  const [selection,setSelection]=useState('quality');
  const [threshold,setThreshold]=useState(70);
  const [count,setCount]=useState('5');
  const [minimum,setMinimum]=useState('8');
  const [maximum,setMaximum]=useState(studio?'90':'60');
  const [autoCount,setAutoCount]=useState(false);
  const [style,setStyle]=useState('mint');
  const [font,setFont]=useState('Poppins');
  const [quality,setQuality]=useState('high');
  const [speed,setSpeed]=useState('1');
  const [mode,setMode]=useState<TranscriptionMode>('quick');
  const [captionScript,setCaptionScript]=useState<CaptionScript>('original');
  const [speechLanguage,setSpeechLanguage]=useState<SpeechLanguage>('auto');
  const [generate,setGenerate]=useState(true);
  const [render,setRender]=useState(true);
  const [jobId,setJobId]=useState<string|null>(null);
  const [job,setJob]=useState<Job|null>(null);
  const [sending,setSending]=useState(false);
  const [error,setError]=useState('');
  const [progressVisible,setProgressVisible]=useState(true);
  const [noticeStarted,setNoticeStarted]=useState(false);
  const [sourcePreview,setSourcePreview]=useState<SourcePreview|null>(null);
  const [previewLoading,setPreviewLoading]=useState(false);
  const [previewFailed,setPreviewFailed]=useState(false);
  const [lengthChoice,setLengthChoice]=useState(studio?'8-90':'custom');
  const active=sending||!!jobId&&job?.status!=='error';
  useEffect(()=>{try{setJobId(localStorage.getItem(storageKey));}catch{/* Storage can be unavailable in private browsers. */}},[]);
  async function openProject(id:string) {
    try{localStorage.removeItem(storageKey);}catch{}
    setJobId(null);
    await onProject(id);
  }
  useEffect(()=>{
    if(!jobId)return;
    let cancelled=false;
    let timer:ReturnType<typeof setTimeout>;
    async function poll(){
      try{
        const response=await guestFetch(`/api/imports/${jobId}`,{cache:'no-store'});
        if(response.status===401||response.status===404){
          if(cancelled)return;
          try{localStorage.removeItem(storageKey);}catch{}
          setJobId(null);setJob(null);
          setError('That earlier import is unavailable in this guest workspace. You can start a new import.');
          return;
        }
        const data=decodeApiResponse<Job>(await response.text(),response.status);
        if(cancelled)return;
        setJob(data);
        setError('');
        if(data.options?.url)setUrl(data.options.url);
        if(data.status==='ready'&&data.project_id){await openProject(data.project_id);return;}
        if(data.status==='error')return;
      }catch(e){if(!cancelled)setError(apiErrorMessage(e,'Could not check import progress.'));}
      if(!cancelled)timer=setTimeout(()=>void poll(),1500);
    }
    void poll();
    return ()=>{cancelled=true;clearTimeout(timer);};
    // Opening a completed project must not restart the polling interval.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  },[jobId]);
  async function submit(event:React.FormEvent){
    event.preventDefault();if(active||previewLoading||generate&&!validDuration(minimum,maximum))return;
    if(studio&&!sourcePreview&&!previewFailed){
      setPreviewLoading(true);setError('');
      try{
        const response=await guestFetch('/api/source-preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:url.trim()})});
        setSourcePreview(decodeApiResponse<SourcePreview>(await response.text(),response.status));
      }catch(e){setPreviewFailed(true);setError(apiErrorMessage(e,'Source preview unavailable. You can still try importing the link.'));}
      finally{setPreviewLoading(false);}
      return;
    }
    setSending(true);setError('');setJob(null);setJobId(null);setProgressVisible(true);setNoticeStarted(true);
    try{localStorage.removeItem(storageKey);}catch{}
    try{
      const response=await guestFetch('/api/imports',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({caption_script:captionScript,speech_language:speechLanguage,aspect,framing,caption_animation:animation,url:url.trim(),source_kind:'any',selection_mode:selection,minimum_score:threshold,clip_count:autoCount?100:Number(count),auto_count:autoCount,min_duration:generate?Number(minimum):8,max_duration:generate?Number(maximum):60,style,subtitle_font:font,speed:Number(speed),render_quality:quality,transcription_mode:mode,auto_generate:generate,auto_render:generate&&render})});
      const data=decodeApiResponse<Job>(await response.text(),response.status);
      setJob(data);setJobId(data.id);
      try{localStorage.setItem(storageKey,data.id);}catch{}
    }catch(e){setError(apiErrorMessage(e,'Could not start import.'));}
    finally{setSending(false);}
  }
  const phase=sending?'Sending your link':job?.project_progress?.stage==='rendering'?'Rendering clip previews':job?.project_progress?.stage==='transcribing'?'Transcribing audio':job?.project_progress?.stage==='analyzing'?'Finding highlight moments':job?.status==='processing'?'Creating captions & clips':job?.status==='importing'?'Downloading your video':'Link queued for processing';
  const stageProgress=job?.project_progress?.stage==='transcribing'?job.project_progress.transcription_progress:job?.status==='importing'?job.progress:null;
  return <section className={`link-importer ${studio?'youtube-importer':''}`} aria-label={studio?'Public link to clips':'Import video from a link'}>
    {progressVisible&&(sending||jobId||noticeStarted&&error)&&<ProcessingNotice title={job?.status==='error'||error&&!active?'Import needs attention':phase} message={job?.error||error||job?.message||'Starting automatic video processing…'} progress={stageProgress} details={job?.project_progress?.total?`${job.project_progress.ready} / ${job.project_progress.total} clip previews ready`:job?.status==='importing'?`${(job.downloaded_bytes/1024**2).toFixed(1)} MB downloaded`:undefined} failed={job?.status==='error'||!!error&&!active} onDismiss={()=>setProgressVisible(false)}/>}
    {!progressVisible&&active&&<ProcessingReopen onShow={()=>setProgressVisible(true)}/>}
    <div className="link-heading"><span className="upload-symbol"><Link2 size={23}/></span><div><h2>{studio?'Paste a video link. Get your clips.':'One link. A whole new set of clips.'}</h2><p>{'YouTube · TikTok · Instagram · Facebook · other supported public video sites and direct video links'}</p></div><span className="link-badge"><Sparkles size={12}/>{'Link to clips'}</span></div>
    {studio&&<div className="youtube-steps"><span>01 · Paste your link</span><span>02 · AI prepares previews</span><span>03 · Review, edit & export</span><p>Public video link paste karein. AI clips banayega; pehle preview dekhein, phir apni pasand ke clips download karein.</p></div>}
    <form onSubmit={e=>void submit(e)}>
      <div className="platform-shortcuts" role="group" aria-label="Video source shortcuts">{[['YouTube','▶'],['TikTok','♪'],['Instagram','◎'],['Facebook','f'],['Direct URL','↗']].map(([name,icon])=><button type="button" key={name} aria-pressed={platform===name} disabled={active} onClick={()=>{setPlatform(name);urlInput.current?.focus();}}><span>{icon}</span>{name}</button>)}{onUpload&&<button type="button" disabled={active} onClick={onUpload}><Link2 size={13}/>Upload file</button>}</div>
      <div className="link-input-row"><label>Public video link<input ref={urlInput} type="url" inputMode="url" required maxLength={4096} disabled={active||previewLoading} placeholder={`Paste a public ${platform==='Direct URL'?'video file':platform} link…`} value={url} onChange={e=>{setUrl(e.target.value);setSourcePreview(null);setPreviewFailed(false);setError('');}}/></label>{(!studio||!sourcePreview)&&<button className="primary" disabled={active||previewLoading||!url.trim()||generate&&!validDuration(minimum,maximum)} type="submit">{active||previewLoading?<LoaderCircle className="spin" size={16}/>:<Link2 size={16}/ >}{previewLoading?'Reading video…':active?'Importing…':generate?(studio?(sourcePreview?'Create AI Clips':previewFailed?'Import without preview':'Get clips'):'Import & create clips'):'Import video'}</button>}</div>
      {previewLoading&&<p role="status">Reading the source title and duration. No video has been downloaded yet.</p>}
      {studio&&sourcePreview&&<article className="source-preview-card" aria-label="Selected source video"><div className="source-preview-media"><SourceImage src={sourcePreview.thumbnail} alt="Source video thumbnail"/><span>{sourcePreview.duration==null?'Duration unavailable':`${Math.floor(sourcePreview.duration/60)}:${String(Math.floor(sourcePreview.duration%60)).padStart(2,'0')}`}</span></div><h3>{sourcePreview.title}</h3><p>{sourcePreview.platform} · Source metadata</p><small>The playable preview appears here after import.</small></article>}
      {studio&&<div className="import-simple-settings"><div className="import-language-options"><div className="subtitle-language-options"><label>Caption language<select aria-label="Import Subtitle script" value={captionScript} disabled={active||previewLoading} onChange={e=>setCaptionScript(e.target.value as CaptionScript)}>{CAPTION_LANGUAGES.map(([value,label])=><option key={value} value={value}>{captionOptionLabel(value,label,languageCapabilities)}</option>)}</select></label><label>Source speech<select aria-label="Import Spoken language" value={speechLanguage} disabled={active||previewLoading} onChange={e=>setSpeechLanguage(e.target.value as SpeechLanguage)}>{SPEECH_LANGUAGES.map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label><small role="status">{languageGuidance(captionScript,speechLanguage,languageCapabilities)}</small><label>Processing quality<select aria-label="Processing quality" value={quality} disabled={active||previewLoading} onChange={e=>setQuality(e.target.value)}><option value="fast">Quick - 480p</option><option value="standard">Balanced - 720p</option><option value="high">Full HD - 1080p</option></select></label><small>480p/720p process fewer pixels and are quicker. This sets download and export quality; choose 1080p for full detail. Quick speech uses the same multilingual model as Balanced, with independent decoding for regional speech; review captions.</small></div><label>Video ratio<select aria-label="Import aspect ratio" value={aspect} disabled={active||previewLoading} onChange={e=>setAspect(e.target.value)}>{aspectOptions.map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label><label>Framing<select aria-label="Import framing" value={framing} disabled={active||previewLoading} onChange={e=>setFraming(e.target.value)}><option value="follow">Full screen - follow visible face</option><option value="crop">Full screen - fixed crop</option><option value="fit">Keep full source - allow padding</option></select></label><label className="import-length-control">Clip length<select aria-label="Import clip length" disabled={active} value={lengthChoice} onChange={e=>{const value=e.target.value;setLengthChoice(value);if(value!=='custom'){const [a,b]=value.split('-');setMinimum(a);setMaximum(b);}}}><option value="8-90">Auto · 8–90 seconds</option><option value="8-30">Under 30 seconds</option><option value="30-60">30–60 seconds</option><option value="60-90">60–90 seconds</option><option value="90-180">90 seconds–3 minutes</option><option value="custom">Custom duration</option></select></label></div></div>}
      <label className="check-field"><input type="checkbox" aria-label="Import automatic clip quantity" checked={autoCount} disabled={active} onChange={e=>setAutoCount(e.target.checked)}/>Auto clip quantity - distinct qualified moments, up to 100</label>
      <div className="import-core-options"><label>Clips to generate<small>Requested maximum. Source length and quality rules can produce fewer clips.</small><input aria-label="Clips to generate" type="number" min="1" max="100" step="1" required value={count} disabled={active||!generate||autoCount} onChange={e=>setCount(e.target.value)}/><input aria-label="Clip count slider" type="range" min="1" max="100" value={Math.max(1,Math.min(100,Number(count)||1))} disabled={active||!generate||autoCount} onChange={e=>setCount(e.target.value)}/></label>{(!studio||lengthChoice==='custom')&&<ClipDuration prefix="Import " minimum={minimum} maximum={maximum} onChange={(a,b)=>{setMinimum(a);setMaximum(b);}} disabled={active||!generate}/>}</div>
      {studio&&sourcePreview&&Number(count)>Math.max(1,Math.floor((sourcePreview.duration||0)/Number(minimum)))&&!autoCount&&sourcePreview.duration!=null&&<p className="link-note" role="status">At your minimum duration, this source fits at most {Math.max(1,Math.floor(sourcePreview.duration/Number(minimum)))} separate clips before quality filtering. Shorter clips can allow more moments.</p>}
      <details className="import-customization"><summary>Customize clips <span>{autoCount?'Auto quantity':`${count} clips`} · {captionScript.replaceAll('_',' ')} captions · {quality==='high'?'1080p':quality==='standard'?'720p':'480p'}</span></summary><div className="studio-config-heading"><h3>Clip settings</h3><p>Optional settings. Your choices apply to generation and remain editable later.</p></div>
      <div className="quick-preset-section"><span>Quick caption presets</span><div className="quick-preset-grid">{[
        ['Reels','✦','9:16 full screen - Mint','mint','Poppins','pop','vertical'],['Podcast','♬','Clean · Readable','clean','Poppins','fade','vertical'],['Gaming','◈','Bold · High energy','yellow','Bangers','bounce','vertical'],['Motivational','♡','Strong · Focused','clean','Anton','pop','vertical'],['Cinematic','▣','Elegant · Restrained','elegant','Georgia','fade','original'],
      ['Neon glow','*','Pink glow - readable','neon','Poppins','fade','vertical'],['Neon highlight','*','Active word - glow','neon_highlight','Poppins','pop','vertical'],
      ].map(([name,icon,description,design,family,motion,frame])=><button type="button" key={name} aria-pressed={preset===name} disabled={active} onClick={()=>{setPreset(name);setStyle(design);setFont(family);setAnimation(motion);setAspect(frame);}}><span className="preset-glyph">{icon}</span><strong>{name}</strong><small>{description}</small></button>)}</div><small>Presets change captions and framing. Highlight ranking stays transcript-based.</small></div>
      <div className="link-options"><label>Selection mode<select aria-label="Import selection mode" disabled={active||!generate} value={selection} onChange={e=>setSelection(e.target.value)}><option value="quality">Quality first · only qualified moments</option><option value="all">Explore all · legacy suggestions</option></select></label><label>Minimum engagement score<input aria-label="Import minimum engagement score" required type="number" min="0" max="100" step="1" value={threshold} disabled={active||!generate||selection!=='quality'} onChange={e=>setThreshold(Number(e.target.value))}/><input aria-label="Engagement score slider" type="range" min="0" max="100" value={threshold} disabled={active||!generate||selection!=='quality'} onChange={e=>setThreshold(Number(e.target.value))}/></label></div>
      <div className="link-options"><label>Caption design<select value={style} disabled={active} onChange={e=>setStyle(e.target.value)}>{subtitleStyles.map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label><label>Speech recognition<select value={mode} disabled={active||!generate} onChange={e=>setMode(e.target.value as TranscriptionMode)}>{recognitionChoices(captionScript,speechLanguage).map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label></div>
      <div className="import-quality"><label>Video quality<select aria-label="Video quality" aria-describedby="import-quality-help" value={quality} disabled={active} onChange={e=>setQuality(e.target.value)}><option value="fast">480p · Fast</option><option value="standard">720p · HD</option><option value="high">1080p · Full HD</option></select></label><small id="import-quality-help">Applies to source download quality (when available) and generated clips. Higher quality takes more processing; low-resolution sources cannot gain missing detail.</small></div>
      <div className="link-options">{!studio&&<label>Aspect ratio<select aria-label="Import aspect ratio" value={aspect} disabled={active} onChange={e=>setAspect(e.target.value)}>{aspectOptions.map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>}<label>Caption font<select aria-label="Caption font" value={font} disabled={active} style={{fontFamily:font}} onChange={e=>setFont(e.target.value)}>{subtitleFonts.map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label><label>Clip speed<select aria-label="Import clip speed" value={speed} disabled={active} onChange={e=>setSpeed(e.target.value)}>{speedOptions.map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label></div>
      {!studio&&<SubtitleOptions prefix="Import " script={captionScript} language={speechLanguage} onScript={setCaptionScript} onLanguage={setSpeechLanguage} disabled={active}/>}
      <div className="link-toggles"><label className="check-field"><input type="checkbox" checked={generate} disabled={active} onChange={e=>setGenerate(e.target.checked)}/>Generate captions & clips automatically</label><label className="check-field"><input type="checkbox" checked={render} disabled={active||!generate} onChange={e=>setRender(e.target.checked)}/>Prepare video previews automatically (no download)</label></div>
      </details>
      {studio&&sourcePreview&&<button className="primary import-create-button" disabled={active||previewLoading||generate&&!validDuration(minimum,maximum)} type="submit">{active?<LoaderCircle className="spin" size={18}/>:<Sparkles size={18}/ >}{active?'Processing video?':generate?'Create AI Clips':'Import video'}</button>}
    </form>
    {job&&<div className="link-job" role="status"><strong>{job.status==='error'?'Import needs attention':job.message}</strong>{job.status==='importing'&&<><progress value={job.progress??undefined} max={100}/><small>{job.progress!==null?`${job.progress}% · `:''}{(job.downloaded_bytes/1024**2).toFixed(1)} MB downloaded</small></>}{job.status==='processing'&&<small>Download complete. Captions and highlights are processing on this machine.</small>}{job.error&&<p role="alert">{job.error}</p>}{job.project_id&&<button className="text-button" onClick={()=>void openProject(job.project_id!)}>Open imported video<ArrowRight size={14}/></button>}</div>}
    {error&&<p className="link-error" role="alert">{error}</p>}
    <p className="link-note">Downloads are manual: preview generated clips in the editor, then download only your choices. Quality first may return fewer clips or none; scores use transcript heuristics and available audio/visual measurements, not view predictions. Paste a single public video/reel, not a playlist or profile. Support depends on the website and this specific video; not every platform or link is downloadable. No login cookies are imported. Private, DRM, region or bot restrictions may prevent downloading. Up to 2 GB / 4 hours. Caption fonts, colors and effects remain editable afterwards.</p>
  </section>;
}
