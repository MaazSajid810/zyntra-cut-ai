import CreatorPlatform from '../components/CreatorPlatform';
export default async function Page({searchParams}:{searchParams:Promise<{url?:string;prompt?:string;project?:string}>}){const p=await searchParams;return <CreatorPlatform view="Create" seedUrl={p.url||''} seedPrompt={p.prompt||''} seedProject={p.project||''}/>;}
