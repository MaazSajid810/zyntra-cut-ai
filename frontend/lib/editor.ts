export const SOUND_EFFECTS=[['none','None'],['pop','Pop'],['ding','Ding'],['whoosh','Whoosh'],['click','Click'],['success','Success chime'],['error','Error buzz'],['impact','Bass impact'],['sparkle','Sparkle'],['riser','Riser'],['scratch','Scratch']] as const;
export type EffectSettings = {
  image_asset_id:string|null; image_start:number; image_end:number; image_layout:'overlay'|'full'; image_fit:'contain'|'cover'; image_opacity:number; image_width:number; image_x:number; image_y:number;
  caption_offset:number;
  watermark_enabled:boolean; watermark_text:string; watermark_opacity:number; watermark_size:number; watermark_color:string; watermark_x:number; watermark_y:number;
  logo_asset_id:string|null; logo_opacity:number; logo_width:number; logo_x:number; logo_y:number;
  filler_asset_id:string|null; filler_start:number; filler_end:number; filler_layout:'full'|'pip';
  music_asset_id:string|null; music_volume:number; sound_effect:typeof SOUND_EFFECTS[number][0]; sound_at:number; sound_volume:number;
  transition:'none'|'fade'|'white'; transition_duration:number;
  caption_mode:'phrase'|'karaoke'|'word'; caption_animation:'none'|'pop'|'bounce'|'scale'|'fade'; highlight_color:string; sticker_enabled:boolean; audio_leveling:boolean; denoise:boolean; zoom:'none'|'gentle'|'punch';
  sticker_timing:'full'|'start'|'middle'|'end'|'custom'; sticker_animation:'none'|'pop'|'fade'|'slide'; sticker_duration:number; sticker_at:number; voice_strength:number; cover_source_captions:boolean; source_caption_y:number; source_caption_height:number;
  speed:number;
  hide_webcam:boolean; webcam_x:number; webcam_y:number; webcam_width:number; webcam_height:number;
  framing:'fit'|'crop'; crop_x:number; crop_y:number;
  aspect:'vertical'|'square'|'original'|'landscape'|'portrait';
  style:'mint'|'clean'|'yellow'|'boxed'|'neon'|'neon_highlight'|'minimal'|'cyan'|'orange'|'red'|'comic'|'elegant'|'shadow'|'none';
  voice_effect:'none'|'deep'|'high'|'radio'|'echo'|'mute';
  video_effect:'none'|'vivid'|'warm'|'cool'|'mono'|'vintage'|'mirror'|'cinematic'|'sepia'|'soft'|'sharpen'|'blur';
  render_quality:'fast'|'standard'|'high'; output_format:'mp4'|'webm';
  subtitle_font:'Arial'|'Impact'|'Georgia'|'Anton'|'Bebas Neue'|'Poppins'|'Righteous'|'Bangers'|'Lobster'|'Pacifico'|'Kalam'; subtitle_size:number;
  subtitle_color:string|null; subtitle_position:'top'|'center'|'bottom'; subtitle_uppercase:boolean;
  sticker:'none'|'subscribe'|'follow'|'like'; sticker_position:'top-left'|'top-right'|'bottom-left'|'bottom-right'; sticker_size:number;
  overlay_text:string; overlay_position:'top'|'center'|'bottom';
};
export type Clip = Partial<EffectSettings> & Pick<EffectSettings,'aspect'|'style'> & {id:string; batch_id?:string; title:string; start:number; end:number; status:string; score:number|null; reason:string; selection_evidence?:{factors:Record<string,number>;opening_excerpt:string;recommendations:string[];limitations:string}; file:string|null; error:string|null};
export const defaultEffects:EffectSettings = {image_asset_id:null,image_start:0,image_end:3,image_layout:"overlay",image_fit:"contain",image_opacity:1,image_width:35,image_x:50,image_y:50,caption_offset:0,watermark_enabled:false,watermark_text:'',watermark_opacity:.18,watermark_size:72,watermark_color:'#ffffff',watermark_x:50,watermark_y:50,logo_asset_id:null,logo_opacity:.4,logo_width:18,logo_x:90,logo_y:10,filler_asset_id:null,filler_start:0,filler_end:3,filler_layout:'full',music_asset_id:null,music_volume:.15,sound_effect:'none',sound_at:0,sound_volume:.5,transition:'none',transition_duration:.35,sticker_timing:'full',sticker_animation:'none',sticker_duration:3,sticker_at:0,voice_strength:1,cover_source_captions:false,source_caption_y:75,source_caption_height:25,caption_mode:'karaoke',caption_animation:'pop',highlight_color:'#ffdf35',sticker_enabled:false,audio_leveling:false,denoise:false,zoom:'none',speed:1,hide_webcam:false,webcam_x:75,webcam_y:0,webcam_width:25,webcam_height:35,framing:'fit',crop_x:50,crop_y:50,aspect:'original',style:'mint',voice_effect:'none',video_effect:'none',render_quality:'high',output_format:'mp4',subtitle_font:'Poppins',subtitle_size:56,subtitle_color:null,subtitle_position:'bottom',subtitle_uppercase:false,overlay_text:'',overlay_position:'top',sticker:'none',sticker_position:'top-right',sticker_size:30};
export function resolveEffects(clip?:Clip):EffectSettings {
  const result = {...defaultEffects};
  for(const key of Object.keys(defaultEffects) as (keyof EffectSettings)[]) {
    if(clip&&clip[key]!==undefined) Object.assign(result,{[key]:clip[key]});
  }
  if(clip&&clip.voice_strength===undefined)result.voice_strength=.5;
  if(clip&&!clip.render_quality) result.render_quality='standard';
  return result;
}
export const speedOptions:[string,string][] = [1,1.2,1.25,1.5,1.75,2,2.5,3,3.5,4].map(n=>[String(n),`${n}x`]);
export const subtitleFonts:[EffectSettings['subtitle_font'],string][] = [['Arial','Arial · classic'],['Impact','Impact · heavy'],['Georgia','Georgia · serif'],['Anton','Anton · bold headlines'],['Bebas Neue','Bebas Neue · tall caps'],['Poppins','Poppins · modern'],['Righteous','Righteous · rounded'],['Bangers','Bangers · comic'],['Lobster','Lobster · script'],['Pacifico','Pacifico · handwritten'],['Kalam','Kalam · marker']];
export const subtitleStyles:[EffectSettings['style'],string][] = [['mint','Mint outline'],['clean','Clean white'],['yellow','Yellow highlight'],['boxed','Dark box'],['neon','Neon glow'],['neon_highlight','Neon word highlight'],['minimal','Minimal'],['cyan','Electric cyan'],['orange','Orange label'],['red','Red banner'],['comic','Comic outline'],['elegant','Elegant italic'],['shadow','Heavy shadow'],['none','No subtitles']];
