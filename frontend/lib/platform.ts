import {decodeApiResponse,guestFetch} from './api';
import {type Clip} from './editor';
export type WorkspaceProject=import('../app/LegacyWorkspace').Project;
export async function platformApi<T>(path:string,options?:RequestInit):Promise<T>{const r=await guestFetch('/api'+path,options);return decodeApiResponse<T>(await r.text(),r.status);}
export const jsonBody=(body:unknown,method='POST'):RequestInit=>({method,headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
export const editorUrl=(project:string,clip?:string)=>'/editor?project='+encodeURIComponent(project)+(clip?'&clip='+encodeURIComponent(clip):'');
export const clock=(seconds:number)=>`${Math.floor(seconds/60)}:${Math.floor(seconds%60).toString().padStart(2,'0')}`;
