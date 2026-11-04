let sessionReady:Promise<void>|null=null;

/** Describe a browser transport failure without mislabelling an HTTP rejection. */
export function apiErrorMessage(error:unknown,fallback:string):string {
  if(error instanceof Error){
    if((error instanceof TypeError||error.name==='NetworkError')&&/fetch|network|load failed/i.test(error.message)){
      return 'Connection to the app was interrupted. Wait a moment, then retry. If you submitted a video, check Library before submitting it again.';
    }
    return error.message;
  }
  return fallback;
}

export function ensureGuestSession():Promise<void>{
  if(!sessionReady) sessionReady=fetch('/api/session',{credentials:'same-origin',cache:'no-store'}).then(async response=>{
    decodeApiResponse(await response.text(),response.status);
  }).catch(error=>{sessionReady=null;throw error;});
  return sessionReady;
}
export async function guestFetch(input:string,options?:RequestInit):Promise<Response>{
  await ensureGuestSession();
  const response=await fetch(input,{...options,credentials:'same-origin',cache:'no-store'});
  if(response.status===401) sessionReady=null;
  return response;
}

/** Both fetch and XMLHttpRequest can receive plain text from a failed proxy. */
export function decodeApiResponse<T>(text: string, status: number): T {
  let data: unknown;
  try { data = JSON.parse(text); } catch { /* Handle non-JSON proxy errors below. */ }
  if (status < 200 || status >= 300) {
    const detail = data && typeof data === 'object' && 'detail' in data ? data.detail : null;
    if (typeof detail === 'string') throw new Error(detail);
    if (status === 413) throw new Error('This upload is too large. Choose a video up to 2 GB.');
    if ([502, 503, 504].includes(status)) throw new Error(`The video server is unavailable or timed out (HTTP ${status}). Check that the Python backend is running and retry.`);
    throw new Error(`The server could not complete this request (HTTP ${status}). Please retry. If it continues, check the server logs.`);
  }
  if (status === 204) return undefined as T;
  if (data === undefined) throw new Error('The server returned an invalid response. Refresh the page and retry.');
  return data as T;
}
