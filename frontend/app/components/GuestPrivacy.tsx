'use client';
import {useState} from 'react';
import {guestFetch,decodeApiResponse} from '../../lib/api';

export default function GuestPrivacy({onRestore}:{onRestore:()=>Promise<void>}){
  const [key,setKey]=useState('');
  const [busy,setBusy]=useState(false);
  const [message,setMessage]=useState('');
  async function restore(){
    setBusy(true);setMessage('');
    try{
      const response=await guestFetch('/api/session/claim-legacy',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key:key.trim()})});
      const result=decodeApiResponse<{projects:number}>(await response.text(),response.status);
      setKey('');setMessage(`Restored ${result.projects} previous projects to this private browser workspace.`);
      await onRestore();
    }catch(error){setMessage(error instanceof Error?error.message:'Could not restore previous projects.');}
    finally{setBusy(false);}
  }
  return <section className="guest-privacy" aria-label="Guest workspace privacy">
    <h3>Your browser. Your private workspace.</h3>
    <p>No signup or login needed. A private browser cookie opens your projects. Other browser sessions cannot access them. Keep using this browser/profile; clearing cookies, using private browsing, or switching devices loses access. Access lasts 180 days from your latest app visit. People sharing this browser/profile also share this workspace.</p>
    <p>Login ki zaroorat nahi. Aapka kaam isi browser/profile mein khulta hai. Cookies clear karne, private window band karne ya browser/device badalne par purane kaam ka access nahi milega. Ek hi browser/profile share karne walay log ek workspace dekhte hain.</p>
    <p>Open a project and choose a clip, then <strong>Delete this clip</strong> removes only that clip. <strong>Delete project</strong> removes the whole project, including its source video and exports. Deletion asks for confirmation and cannot be undone. Apna project ya clip khol kar delete karein; source aur sab clips sirf Delete project se hatenge.</p>
    <details><summary>Restore projects from the earlier local version / Purane local projects wapas layen</summary>
      <p>Only for the owner upgrading the earlier local app: open <code>data/legacy-workspace-key.txt</code> in VS Code and paste its one-time key here. This file is not publicly served. After restoring, the projects belong to this browser workspace and the key stops working. Pehle local version ke owner ke liye: file ki key yahan paste karein.</p>
      <label>Local restore key<input type="password" autoComplete="off" value={key} maxLength={43} onChange={e=>setKey(e.target.value)} disabled={busy}/></label>
      <button type="button" className="secondary" disabled={busy||key.trim().length!==43} onClick={()=>void restore()}>{busy?'Restoring…':'Restore previous projects'}</button>
      {message&&<p role="status">{message}</p>}
    </details>
  </section>;
}
