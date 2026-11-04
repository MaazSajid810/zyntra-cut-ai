import {test,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

test('visible quality and quick speech choices submit the selected neon settings',async({page})=>{
  // Explicit upstream fixtures check the UI contract without claiming a download.
  await page.route('**/api/source-preview',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({title:'Neon settings contract fixture',duration:2400,platform:'YouTube',thumbnail:null,url:'https://www.youtube.com/watch?v=abcdefghijk'})}));
  await page.route('**/api/imports',route=>route.fulfill({status:429,contentType:'application/json',body:JSON.stringify({detail:'Explicit test import rejection'})}));
  await page.goto('/dashboard');
  await expect(page.getByLabel('Processing quality',{exact:true})).toBeVisible();
  await expect(page.getByLabel('Processing quality',{exact:true})).toHaveValue('high');
  await page.getByLabel('Processing quality',{exact:true}).selectOption('standard');
  await page.locator('.import-customization>summary').click();
  await expect(page.getByLabel('Video quality',{exact:true})).toHaveValue('standard');
  await expect(page.getByRole('combobox',{name:'Speech recognition',exact:true})).toHaveValue('quick');
  await page.getByRole('button',{name:/Neon highlight/}).click();
  await page.getByLabel('Clips to generate',{exact:true}).fill('30');
  await page.getByLabel('Public video link',{exact:true}).fill('https://www.youtube.com/watch?v=abcdefghijk');
  await page.getByRole('button',{name:'Get clips',exact:true}).click();
  await expect(page.getByRole('article',{name:'Selected source video',exact:true})).toContainText('Neon settings contract fixture');
  const posted=page.waitForResponse(r=>r.url().endsWith('/api/imports')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Create AI Clips',exact:true}).click();
  expect((await posted).request().postDataJSON()).toMatchObject({clip_count:30,style:'neon_highlight',caption_animation:'pop',aspect:'vertical',render_quality:'standard',transcription_mode:'quick'});
  await expect(page.locator('.link-error')).toContainText('Explicit test import rejection');
  for(const width of [1440,390]){
    await page.setViewportSize({width,height:1000});
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
    await page.screenshot({path:`artifacts/neon-import-${width}.png`,fullPage:true,animations:'disabled'});
  }
});

test('neon presets render real clips and shared edits preserve individual source ranges',async({page})=>{
  execFileSync(path.resolve(process.platform==='win32'?'.venv/Scripts/python.exe':'.venv/bin/python'),['-m','scripts.browser_fixture']);
  await page.request.get('/api/session');
  const uploaded=await page.request.post('/api/projects',{multipart:{file:{name:'Neon verification.mp4',mimeType:'video/mp4',buffer:fs.readFileSync('artifacts/browser-fixture.mp4')}}});
  expect(uploaded.status()).toBe(201);
  const project=await uploaded.json(),base='/api/projects/'+project.id;
  try{
    // Manual caption text intentionally has no word alignment: the documented
    // readable-phrase fallback is verified here; pixel/timed-word tests use FFmpeg.
    expect((await page.request.put(base+'/transcript',{data:[{id:0,start:0,end:3,text:'Actual neon caption export.'}]})).status()).toBe(200);
    for(const [title,start,end] of [['First neon range',0,2],['Second neon range',1,3]]){
      expect((await page.request.post(base+'/clips',{data:{title,start,end,style:'clean',render_quality:'fast'}})).status()).toBe(201);
    }
    const original=(await(await page.request.get(base)).json()).clips;
    const ranges=(clips:any[])=>clips.map(({id,title,start,end})=>({id,title,start,end}));
    await page.goto(`/editor?project=${project.id}&clip=${original[0].id}`);
    await page.getByRole('group',{name:'Editing tools',exact:true}).getByRole('button',{name:'Captions',exact:true}).click();
    await page.getByRole('button',{name:'Neon glow',exact:true}).click();
    await expect(page.getByLabel('Subtitle style',{exact:true})).toHaveValue('neon');
    await page.getByRole('button',{name:'Neon word highlight',exact:true}).click();
    await expect(page.getByLabel('Subtitle style',{exact:true})).toHaveValue('neon_highlight');
    const shared=page.waitForResponse(r=>r.url().includes('/clips/settings?include_ready=true')&&r.request().method()==='PUT');
    await page.getByRole('button',{name:'Apply & render all clips',exact:true}).click();
    const response=await shared;expect(response.status()).toBe(200);
    expect(ranges((await response.json()).clips)).toEqual(ranges(original));
    await expect.poll(async()=>{
      const clips=(await(await page.request.get(base)).json()).clips;
      return clips.length===2&&clips.every((c:any)=>c.status==='ready'&&c.style==='neon_highlight'&&c.caption_mode==='karaoke');
    },{timeout:60000}).toBeTruthy();
    await expect(page.getByRole('button',{name:'Export ready',exact:true})).toBeVisible({timeout:60000});
    const video=page.locator('.clip-preview-workspace video');
    await expect.poll(()=>video.evaluate((v:HTMLVideoElement)=>v.readyState)).toBeGreaterThan(1);
    await video.evaluate(async(v:HTMLVideoElement)=>{v.muted=true;await v.play();});
    await expect.poll(()=>video.evaluate((v:HTMLVideoElement)=>v.currentTime)).toBeGreaterThan(.1);
    await video.evaluate((v:HTMLVideoElement)=>v.pause());
    const download=page.waitForEvent('download');
    await page.getByRole('link',{name:'Download MP4',exact:true}).click();
    await (await download).saveAs('artifacts/neon-browser-export.mp4');
    for(const width of [1440,390]){
      await page.setViewportSize({width,height:1000});
      expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
      await page.screenshot({path:`artifacts/neon-editor-${width}.png`,fullPage:true,animations:'disabled'});
    }
  }finally{await page.request.delete(base,{timeout:10000}).catch(()=>{});}
});
