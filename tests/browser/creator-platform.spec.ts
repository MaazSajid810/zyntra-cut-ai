import {test,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

test('independent platform navigation, discovery filters, source handoff and mobile layout',async({page})=>{
 await page.route('**/api/discover?**',async route=>{
  // Deliberate upstream UI fixture; not a claim of successful live discovery.
  const category=new URL(route.request().url()).searchParams.get('category');
  await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({items:[{id:'abcdefghijk',title:category+' discovery fixture',channel:'Test source',url:'https://www.youtube.com/watch?v=abcdefghijk',thumbnail:'/fonts/not-an-image',duration:120,views:null,views_per_hour:null}],observed_at:Date.now()/1000,message:'Public relevance search, not a verified trending chart.',stale:false,source:'Test fixture'})});
 });
 await page.route('**/api/source-preview',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({title:'Explicit source metadata fixture',duration:120,platform:'YouTube',thumbnail:null,url:'https://www.youtube.com/watch?v=abcdefghijk'})}));
 await page.goto('/');await expect(page.getByRole('heading',{name:'AI Clipping',exact:true})).toBeVisible();
 await expect(page.getByLabel('Clips to generate',{exact:true})).toBeVisible();
 await page.getByLabel('Import clip length',{exact:true}).selectOption('custom');
 await expect(page.getByLabel('Import Minimum clip duration',{exact:true})).toBeVisible();
 const nav=page.getByRole('navigation',{name:'Creator navigation'});
 await nav.getByRole('link',{name:'Explore',exact:true}).click();
 await expect(page.getByRole('heading',{name:'All discovery fixture'})).toBeVisible();
 await expect(page.getByText('View count unavailable',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Gaming',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Gaming discovery fixture'})).toBeVisible();
 await page.getByRole('link',{name:'Get clips',exact:false}).click();
 await expect(page.getByLabel('Public video link',{exact:true})).toHaveValue('https://www.youtube.com/watch?v=abcdefghijk');
 await page.route('**/api/imports',route=>route.fulfill({status:429,contentType:'application/json',body:JSON.stringify({detail:'Explicit import fixture rejection'})}));
 await page.getByRole('button',{name:'Get clips',exact:true}).click();
 await expect(page.getByRole('article',{name:'Selected source video',exact:true})).toContainText('Explicit source metadata fixture');
 await page.getByRole('button',{name:'Create AI Clips',exact:true}).click();
 await expect(page.locator('.link-error')).toContainText('Explicit import fixture rejection');
 for(const name of ['Create','Explore','Wizard','Studio'] as const){
  await nav.getByRole('link',{name,exact:true}).click();
  await expect(nav.getByRole('link',{name,exact:true})).toHaveAttribute('aria-current','page');
  for(const width of [1440,768,390]){
   await page.setViewportSize({width,height:1000});
   expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();
   if(width===1440||width===390)await page.screenshot({path:`artifacts/platform-${name.toLowerCase()}-${width}.png`,fullPage:true,animations:'disabled'});
  }
 }
});

test('Wizard reviews commands then performs actual caption editing and rendering with private saved history',async({page})=>{
 test.setTimeout(150000);const python=path.resolve('.venv/Scripts/python.exe');
 execFileSync(python,['-m','scripts.browser_fixture']);
 await page.request.get('/api/session');
 const uploaded=await page.request.post('/api/projects',{multipart:{file:{name:'Wizard real video.mp4',mimeType:'video/mp4',buffer:fs.readFileSync('artifacts/browser-fixture.mp4')}}});
 expect(uploaded.status()).toBe(201);const p=await uploaded.json(),base='/api/projects/'+p.id;
 try{
  await page.request.put(base+'/transcript',{data:[{id:0,start:0,end:3,text:'Actual captions. Actual output.'}]});
  const created=await page.request.post(base+'/clips',{data:{title:'Wizard caption edit',start:0,end:3,style:'none',render_quality:'fast'}});expect(created.status()).toBe(201);
  const c=(await created.json()).clips[0];
  await page.goto('/wizard');await page.getByLabel('Wizard project',{exact:true}).selectOption(p.id);
  await page.getByLabel('Wizard clip',{exact:true}).selectOption(c.id);
  await page.getByLabel('Your command',{exact:true}).fill('captions yellow');
  await page.getByRole('button',{name:'Review command',exact:true}).click();
  await expect(page.getByRole('region',{name:'Proposed editing action'})).toContainText('style: yellow');
  expect((await(await page.request.get(base)).json()).clips[0].style).toBe('none');
  await page.getByRole('button',{name:'Run this action',exact:true}).click();
  await expect.poll(async()=>(await(await page.request.get(base)).json()).clips[0].status,{timeout:60000}).toBe('ready');
  const saved=(await(await page.request.get(base)).json()).clips[0];expect(saved.style).toBe('yellow');
  await expect(page.locator('.wizard-results video')).toBeVisible();
  const output=await page.request.get(base+'/media/'+c.id);expect(output.status()).toBe(200);fs.writeFileSync('artifacts/wizard-real-export.mp4',await output.body());
  const info=JSON.parse(execFileSync(python,['-c',"from backend import media; import json; print(json.dumps(media.probe('artifacts/wizard-real-export.mp4')))"],{encoding:'utf8'}));expect(info.duration).toBeCloseTo(3,1);expect(info.has_audio).toBeTruthy();
  await page.reload();await expect(page.getByRole('log',{name:'Wizard conversation'})).toContainText('captions yellow');
  await page.getByLabel('Your command',{exact:true}).fill('make a flying dragon photorealistic');await page.getByRole('button',{name:'Review command',exact:true}).click();
  await expect(page.locator('.platform-wizard .platform-alert')).toContainText('Local commands');
  await expect(page.getByRole('button',{name:'Run this action',exact:true})).toHaveCount(0);
  await page.getByRole('button',{name:'New chat',exact:true}).click();await expect(page.getByRole('log')).toHaveCount(0);
 }finally{await page.request.delete(base).catch(()=>{});}
});

test('source preview precedes generation and submits custom quantity, duration and language',async({page})=>{
 let imports=0;let body:Record<string,unknown>={};let release!:()=>void;
 const gate=new Promise<void>(resolve=>release=resolve);
 await page.route('**/api/source-preview',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({title:'Explicit metadata contract fixture',duration:2490,platform:'YouTube',thumbnail:null,url:'https://www.youtube.com/watch?v=abcdefghijk'})}));
 await page.route('**/api/imports',async route=>{imports++;body=route.request().postDataJSON();await gate;await route.fulfill({status:429,contentType:'application/json',body:JSON.stringify({detail:'Explicit upstream job rejection fixture'})});});
 await page.goto('/dashboard');
 await page.getByLabel('Public video link',{exact:true}).fill('https://www.youtube.com/watch?v=abcdefghijk');
 await page.getByRole('button',{name:'Get clips',exact:true}).click();
 const source=page.getByRole('article',{name:'Selected source video',exact:true});
 await expect(source).toContainText('Explicit metadata contract fixture');expect(imports).toBe(0);
 await expect(page.getByLabel('Import Subtitle script',{exact:true})).toHaveValue('original');
 for(const value of ['punjabi','pashto','sindhi','spanish'])await expect(page.getByLabel('Import Subtitle script',{exact:true}).locator('option[value='+value+']')).toHaveCount(1);
 for(const value of ['pa','ps','sd','es'])await expect(page.getByLabel('Import Spoken language',{exact:true}).locator('option[value='+value+']')).toHaveCount(1);
 await expect(page.getByLabel('Import aspect ratio',{exact:true})).toBeVisible();
 await page.getByLabel('Import aspect ratio',{exact:true}).selectOption('vertical');
 await page.getByLabel('Import Subtitle script',{exact:true}).selectOption('hindi');
 await page.getByLabel('Import Spoken language',{exact:true}).selectOption('ur');
 await page.getByLabel('Import clip length',{exact:true}).selectOption('60-90');
 await page.getByLabel('Clips to generate',{exact:true}).fill('45');
 await expect(page.getByText('At your minimum duration, this source fits at most 41 separate clips before quality filtering.',{exact:false})).toBeVisible();
 await page.getByLabel('Import clip length',{exact:true}).selectOption('30-60');
 try{
  await page.getByRole('button',{name:'Create AI Clips',exact:true}).click();
  await expect(page.getByRole('region',{name:'Video processing status',exact:true})).toContainText('Sending your link');
  expect(imports).toBe(1);expect(body).toMatchObject({clip_count:45,min_duration:30,max_duration:60,caption_script:'hindi',speech_language:'ur',aspect:'vertical',auto_generate:true,auto_render:true});
 }finally{release();}
 await expect(page.locator('.link-error')).toContainText('Explicit upstream job rejection fixture');
 await page.getByLabel('Public video link',{exact:true}).fill('https://www.youtube.com/watch?v=lmnopqrstuv');
 await expect(source).toHaveCount(0);await expect(page.getByRole('button',{name:'Get clips',exact:true})).toBeVisible();
});

test('failed source metadata offers an explicit import retry with visible errors',async({page})=>{
 let imports=0;
 await page.route('**/api/source-preview',route=>route.fulfill({status:502,contentType:'application/json',body:JSON.stringify({detail:'Explicit metadata rejection fixture'})}));
 await page.route('**/api/imports',route=>{imports++;return route.fulfill({status:429,contentType:'application/json',body:JSON.stringify({detail:'Explicit import rejection fixture'})});});
 await page.goto('/dashboard');await page.getByLabel('Public video link',{exact:true}).fill('https://example.com/video.mp4');
 await page.getByRole('button',{name:'Get clips',exact:true}).click();
 await expect(page.locator('.link-error')).toContainText('Explicit metadata rejection fixture');expect(imports).toBe(0);
 await page.getByRole('button',{name:'Import without preview',exact:true}).click();
 await expect(page.locator('.link-error')).toContainText('Explicit import rejection fixture');expect(imports).toBe(1);
});

test('Create uploads a real source, generates previews and preserves project deletion',async({page})=>{
 test.setTimeout(150000);execFileSync(path.resolve('.venv/Scripts/python.exe'),['-m','scripts.browser_fixture']);
 await page.goto('/dashboard');let projectId='',downloads=0;page.on('download',()=>downloads++);
 try{
  const posted=page.waitForResponse(r=>r.url().endsWith('/api/projects')&&r.request().method()==='POST');
  await page.locator('input[type=file]').setInputFiles({name:'Platform upload.mp4',mimeType:'video/mp4',buffer:fs.readFileSync('artifacts/browser-fixture.mp4')});
  const p=await(await posted).json();projectId=p.id;
  await expect(page).toHaveURL(new RegExp('/dashboard\\?project='+p.id));
  await expect(page.getByRole('heading',{name:'Platform upload.mp4',exact:true,level:1})).toBeVisible();
  await page.request.put('/api/projects/'+p.id+'/transcript',{data:[{id:0,start:0,end:3,text:'A real source for the platform workflow.'}]});
  await page.reload();await page.getByLabel('Selection mode',{exact:true}).selectOption('all');
  await page.getByLabel('Number of clips',{exact:true}).fill('1');await page.getByLabel('Subtitle script',{exact:true}).selectOption('original');
  await page.getByText('Clip style & export settings',{exact:true}).click();await page.getByLabel('Generated quality',{exact:true}).selectOption('fast');
  await page.getByRole('button',{name:'Generate 1 new clips',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Rendered clip preview',exact:true})).toBeVisible({timeout:60000});
  await expect(page).toHaveURL(new RegExp('/dashboard\\?project='+p.id));
  expect(downloads).toBe(0);
  await page.getByRole('button',{name:'Close video',exact:false}).click();
  await expect(page.getByRole('heading',{name:'AI Clipping',exact:true})).toBeVisible();
  await page.locator('.platform-open-project').filter({has:page.getByRole('heading',{name:'Platform upload.mp4',exact:true})}).click();
  await expect(page.getByRole('region',{name:'Video processing and clips',exact:true})).toBeVisible();
  const base='/api/projects/'+p.id;
  expect((await page.request.post(base+'/clips',{data:{title:'Second actual range',start:0,end:2,style:'none',render_quality:'fast'}})).status()).toBe(201);
  expect((await page.request.post(base+'/clips',{data:{title:'Third actual range',start:0,end:1,style:'none',render_quality:'fast'}})).status()).toBe(201);
  expect((await page.request.post(base+'/clips/render')).status()).toBe(202);
  await expect.poll(async()=>(await(await page.request.get(base)).json()).clips.filter((c:{status:string})=>c.status==='ready').length,{timeout:60000}).toBe(3);
  await page.reload();
  const actualPreview=page.locator('.review-player video');
  await expect.poll(()=>actualPreview.evaluate((v:HTMLVideoElement)=>v.readyState)).toBeGreaterThan(1);
  await actualPreview.evaluate(async(v:HTMLVideoElement)=>{v.muted=true;await v.play();});
  await expect.poll(()=>actualPreview.evaluate((v:HTMLVideoElement)=>v.currentTime)).toBeGreaterThan(.1);
  await actualPreview.evaluate((v:HTMLVideoElement)=>v.pause());
  await page.getByLabel('Select generated clip Third actual range',{exact:true}).check();
  page.once('dialog',d=>d.accept());await page.getByRole('button',{name:'Delete selected (1)',exact:true}).click();
  await expect(page.locator('.review-card')).toHaveCount(2);
  await expect(actualPreview).toHaveAttribute('src',/\/api\/projects\//);
  await expect.poll(()=>actualPreview.evaluate((v:HTMLVideoElement)=>v.readyState)).toBeGreaterThan(1);
  await page.getByLabel('Sort generated clips',{exact:true}).selectOption('duration');
  await expect(page.locator('.review-card').first()).not.toContainText('Second actual range');
  for(const width of [1440,768,390]){await page.setViewportSize({width,height:1000});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();await page.screenshot({path:`artifacts/dark-clips-${width}.png`,fullPage:true,animations:'disabled'});}
  await page.getByLabel('Select all generated clips',{exact:true}).check();
  page.once('dialog',d=>d.dismiss());await page.getByRole('button',{name:'Delete selected (2)',exact:true}).click();
  await expect(page.getByLabel('Select all generated clips',{exact:true})).toBeChecked();
  page.once('dialog',d=>d.accept());await page.getByRole('button',{name:'Delete selected (2)',exact:true}).click();
  await expect(page.locator('.review-card')).toHaveCount(0);
  expect((await(await page.request.get(base)).json()).clips).toEqual([]);
  expect(downloads).toBe(0);
  await page.setViewportSize({width:1440,height:1000});
  await page.getByRole('complementary',{name:'Workspace sections',exact:true}).getByRole('link',{name:'Home',exact:true}).click();
  await expect(page.getByRole('region',{name:'Video processing and clips',exact:true})).toHaveCount(0);
  await expect(page.getByRole('heading',{name:'Platform upload.mp4',exact:true})).toBeVisible();
  page.once('dialog',d=>d.accept());await page.getByRole('button',{name:'Delete project Platform upload.mp4',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Platform upload.mp4',exact:true})).toHaveCount(0);
  expect((await page.request.get('/api/projects/'+p.id)).status()).toBe(404);
 }finally{if(projectId)await page.request.delete('/api/projects/'+projectId).catch(()=>{});}
});

test('local Studio creates actual PNG and MP4 files, previews them, opens the editor and deletes results',async({page})=>{
 test.setTimeout(150000);let downloads=0;page.on('download',()=>downloads++);
 await page.goto('/studio');
 try{
  await page.getByRole('button',{name:'Image',exact:true}).click();
  await page.getByLabel('Studio title text',{exact:true}).fill('Local PNG test');
  await page.getByRole('button',{name:'Create PNG',exact:true}).click();
  const result=page.getByRole('region',{name:'Finished Studio preview',exact:true});
  await expect(result.locator('img')).toBeVisible({timeout:30000});
  await expect.poll(()=>result.locator('img').evaluate((img:HTMLImageElement)=>img.naturalWidth)).toBe(480);
  expect(downloads).toBe(0);const download=page.waitForEvent('download');await result.getByRole('link',{name:'Download PNG',exact:false}).click();expect((await download).suggestedFilename()).toMatch(/\.png$/);
  await page.getByRole('button',{name:'Video',exact:true}).click();
  await page.getByLabel('Studio title text',{exact:true}).fill('Local motion test');
  await page.getByLabel('Studio duration',{exact:true}).selectOption('3');
  await page.getByRole('button',{name:'Create MP4',exact:true}).click();
  await expect(result.locator('video')).toBeVisible({timeout:60000});
  await expect.poll(()=>result.locator('video').evaluate((v:HTMLVideoElement)=>v.duration)).toBeCloseTo(3,1);
  expect(downloads).toBe(1);
  const jobs=await(await page.request.get('/api/studio')).json();const video=jobs.find((j:{options:{kind:string}})=>j.options.kind==='video');
  const output=await page.request.get('/api/studio/'+video.id+'/media');expect(output.status()).toBe(200);fs.writeFileSync('artifacts/studio-local-motion.mp4',await output.body());
  await page.route('**/api/studio/'+video.id,route=>route.fulfill({status:409,contentType:'application/json',body:JSON.stringify({detail:'Explicit locked-preview fixture'})}),{times:1});
  page.once('dialog',d=>d.accept());await page.getByRole('button',{name:'Delete Studio result Local motion test',exact:true}).click();
  await expect(page.locator('.platform-studio .platform-alert')).toContainText('Explicit locked-preview fixture');
  await expect(result.locator('video')).toHaveAttribute('src','/api/studio/'+video.id+'/media');
  await result.getByRole('link',{name:'Open in full editor',exact:false}).click();
  await expect(page).toHaveURL(new RegExp('/editor\\?project='+video.project_id));
  await expect(page.getByRole('heading',{name:'Local motion test',exact:true})).toBeVisible();
  await page.goto('/studio');page.once('dialog',d=>d.accept());
  await page.getByRole('button',{name:'Delete Studio result Local motion test',exact:true}).click();
  await expect(page.getByRole('button',{name:'Delete Studio result Local motion test',exact:true})).toHaveCount(0);
  expect((await page.request.get('/api/projects/'+video.project_id)).status()).toBe(404);
 }finally{
  for(const job of await(await page.request.get('/api/studio')).json())if(!['queued','rendering'].includes(job.status))await page.request.delete('/api/studio/'+job.id).catch(()=>{});
 }
});
