'use client';

export function validDuration(minimum:string,maximum:string){
  return minimum.trim()!==''&&maximum.trim()!==''&&Number.isFinite(Number(minimum))&&Number.isFinite(Number(maximum))&&Number(minimum)>=3&&Number(maximum)<=180&&Number(minimum)<=Number(maximum);
}

export default function ClipDuration({minimum,maximum,onChange,disabled=false,prefix=''}:{minimum:string;maximum:string;onChange:(min:string,max:string)=>void;disabled?:boolean;prefix?:string}){
  const valid=validDuration(minimum,maximum);
  return <fieldset className="clip-duration"><legend>Clip duration</legend>
    <div className="duration-presets">{[[15,30],[30,60],[60,90]].map(([a,b])=><button key={a} type="button" disabled={disabled} aria-label={`${prefix}Duration ${a} to ${b} seconds`} aria-pressed={Number(minimum)===a&&Number(maximum)===b} onClick={()=>onChange(String(a),String(b))}>{a}-{b}s</button>)}</div>
    <div className="duration-fields"><label>Minimum seconds<input aria-label={`${prefix}Minimum clip duration`} type="number" min="3" max="180" step="0.1" required value={minimum} disabled={disabled} onChange={e=>onChange(e.target.value,maximum)}/></label><label>Maximum seconds<input aria-label={`${prefix}Maximum clip duration`} type="number" min="3" max="180" step="0.1" required value={maximum} disabled={disabled} onChange={e=>onChange(minimum,e.target.value)}/></label></div>
    {!valid&&<p role="alert">Choose 3-180 seconds, with minimum no greater than maximum.</p>}
    <small>AI chooses natural moments within this range, rather than padding clips. Short sources may produce shorter clips. These are source seconds; changing playback speed changes export length.</small>
  </fieldset>;
}
