import Link from 'next/link';
import LegacyWorkspace from '../LegacyWorkspace';
export default async function Page({searchParams}:{searchParams:Promise<{project?:string;clip?:string}>}){const p=await searchParams;return <><Link className="platform-editor-return" href="/dashboard">Back to Create / Explore / Wizard / Studio</Link><LegacyWorkspace initialProjectId={p.project||null} initialClipId={p.clip||null}/></>;}
