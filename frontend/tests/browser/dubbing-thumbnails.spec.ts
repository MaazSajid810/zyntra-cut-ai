import {backendPython} from '../backend-python';
import {test,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

test('Explore uses a stable thumbnail request and readable failure state',async({page})=>{
 await page.route('**/api/discover?**',route=>route.fulfill({contentType:'application/json',body:JSON.stringify({items:[{id:'abcdefghijk',title:'Explicit thumbnail failure fixture',channel:'Test source',url:'https://youtu.be/abcdefghijk',thumbnail:'https://i.ytimg.com/expired-signed-url',duration:20,views:null,views_per_hour:null}],observed_at:Date.now()/1000,message:'Explicit test metadata',stale:false,source:'Fixture'})}));
 let requested=0;
 await page.route('**/api/discover/abcdefghijk/thumbnail',route=>{requested++;return route.fulfill({status:502,body:'Image unavailable'});});
 await page.goto('/explore');
 await expect(page.getByRole('heading',{name:'Explicit thumbnail failure fixture'})).toBeVisible();
 await expect(page.getByRole('img',{name:'Thumbnail unavailable'})).toBeVisible();
 expect(requested).toBe(1);
 await expect(page.locator('.platform-discovery-grid img')).toHaveCount(0);
 await expect(page.getByRole('link',{name:'Get clips',exact:false})).toBeEnabled();
});

test('Transcript can create a real translated offline voice and render it on the same page',async({page})=>{
 test.setTimeout(180000);
 const python=backendPython();
 execFileSync(python,['-c',"from backend import media; media.run(['-f','lavfi','-i','color=c=0x142920:s=320x180:r=15','-i','data/jfk.flac','-shortest','-c:v','libx264','-c:a','aac','artifacts/dubbing-browser-source.mp4'])"]);
 await page.request.get('/api/session');
 const uploaded=await page.request.post('/api/projects',{multipart:{file:{name:'Offline voice verification.mp4',mimeType:'video/mp4',buffer:fs.readFileSync('artifacts/dubbing-browser-source.mp4')}}});
 expect(uploaded.status()).toBe(201);
 const p=await uploaded.json(),base='/api/projects/'+p.id;
 try{
  expect((await page.request.post(base+'/transcribe',{data:{speech_language:'en',transcription_mode:'fast',caption_script:'original',selection_mode:'all',clip_count:1,auto_render:false}})).status()).toBe(202);
  await expect.poll(async()=>(await(await page.request.get(base)).json()).status,{timeout:120000}).toBe('ready');
  await page.goto('/dashboard?project='+p.id);
  await page.getByRole('button',{name:'Transcript',exact:false}).click();
  const panel=page.locator('.dubbing-panel');
  await expect(panel.getByLabel('Voice translation language',{exact:true})).toBeEnabled();
  await panel.getByLabel('Voice translation language',{exact:true}).selectOption('urdu');
  await expect(panel).toContainText('does not animate mouths');
  await panel.getByRole('button',{name:'Translate captions + voice',exact:true}).click();
  await expect.poll(async()=>{
   const response=await page.request.get(base);
   if(!response.ok())return false; // A read-only status poll may recover after a transient proxy reset.
   const saved=await response.json();
   if(saved.dubbing_error)throw new Error(saved.dubbing_error);
   return saved.dubbing?.enabled&&saved.clips.every((c:{status:string})=>c.status==='ready');
  },{timeout:120000}).toBeTruthy();
  await expect(panel).toContainText('Translated voice enabled (ur)');
  const response=await page.request.get(base+'/dubbing/audio');expect(response.status()).toBe(200);expect((await response.body()).length).toBeGreaterThan(10000);
  const saved=await(await page.request.get(base)).json();expect(saved.caption_script).toBe('urdu');expect(saved.dubbing.mouth_animation).toBe(false);
  await page.setViewportSize({width:390,height:900});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();
  await panel.screenshot({path:'artifacts/offline-dubbing-mobile.png',animations:'disabled'});
  await panel.getByRole('button',{name:'Use original audio',exact:true}).click();
  await expect.poll(async()=>(await(await page.request.get(base)).json()).dubbing.enabled).toBe(false);
 }finally{await page.request.delete(base,{timeout:10000}).catch(()=>{});}
});
