import CreatorPlatform from './components/CreatorPlatform';
export default async function Home({searchParams}:{searchParams:Promise<{project?:string}>}){const p=await searchParams;return <CreatorPlatform view="Create" seedProject={p.project||''}/>;}
