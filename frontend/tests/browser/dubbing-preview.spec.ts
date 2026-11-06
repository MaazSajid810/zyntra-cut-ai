import {test,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import fs from 'node:fs';
import {backendPython} from '../backend-python';

test('translated voice plays in the full AV1 video without generating clips and becomes stale after caption edits',async({page})=>{
 execFileSync(backendPython(),['-c',"from backend import media;media.run(['-f','lavfi','-i','color=c=blue:s=160x90:r=5','-t','3','-c:v','libaom-av1','-cpu-used','8','-crf','40','artifacts/dubbing-av1-fixture.mp4'])"]);
 expect((await page.request.get('/api/session')).status()).toBe(200);
 await page.goto('/dashboard');
 const uploaded=await page.request.post('/api/projects',{multipart:{file:{name:'Offline dubbing browser check.mp4',mimeType:'video/mp4',buffer:fs.readFileSync('artifacts/dubbing-av1-fixture.mp4')}}});
 expect(uploaded.status()).toBe(201);const p=await uploaded.json();const base='/api/projects/'+p.id;
 try{
  // Explicit transcript fixture: ASR accuracy is checked separately on real speech.
  execFileSync(backendPython(),['-c',"import sys;from backend import store;s=[{'id':0,'start':.2,'end':2.8,'text':'Hello. Welcome.'}];store.mutate(sys.argv[1],lambda p:p.update(status='ready',language='en',caption_script='original',transcript=s,source_transcript=s))",p.id]);
  await page.goto('/dashboard?project='+p.id);
  await page.getByRole('button',{name:'Translate captions + voice',exact:true}).first().click();
  const panel=page.locator('.dubbing-panel');
  await panel.getByLabel('Voice translation language',{exact:true}).selectOption('urdu');
  await panel.getByRole('button',{name:'Translate captions + voice',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Dubbed video preview',exact:true})).toBeVisible({timeout:90000});
  const video=page.locator('.video-stage video');
  await expect(video).toHaveAttribute('src',/\/dubbing\/video\?v=/);
  await expect.poll(()=>video.evaluate((v:HTMLVideoElement)=>v.readyState)).toBeGreaterThan(1);
  await video.evaluate(async(v:HTMLVideoElement)=>{v.muted=true;await v.play();});
  await expect.poll(()=>video.evaluate((v:HTMLVideoElement)=>v.currentTime)).toBeGreaterThan(.1);
  await video.evaluate((v:HTMLVideoElement)=>v.pause());
  await expect(panel.getByRole('link',{name:'Download dubbed video'})).toBeVisible();
  await page.getByRole('button',{name:'Compare original audio',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Source preview',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Play dubbed video',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Dubbed video preview',exact:true})).toBeVisible();
  const project=await(await page.request.get(base)).json();
  expect(project.clips).toHaveLength(0);
  expect((await page.request.put(base+'/transcript',{data:[{...project.transcript[0],text:project.transcript[0].text+'!'}]})).status()).toBe(200);
  expect((await page.request.get(base+'/dubbing/video')).status()).toBe(409);
  await page.reload();await page.getByRole('button',{name:'Translate captions + voice',exact:true}).first().click();
  await expect(panel.getByText(/Captions changed/)).toBeVisible();
 }finally{
  await page.locator('video,audio').evaluateAll(items=>items.forEach(item=>{const media=item as HTMLMediaElement;media.pause();media.removeAttribute('src');media.load();}));
  expect((await page.request.delete(base)).status()).toBe(204);
 }
});
