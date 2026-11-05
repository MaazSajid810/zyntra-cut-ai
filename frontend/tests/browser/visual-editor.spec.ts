import {backendPython} from '../backend-python';
import {test,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

test('link customization is optional and preserved when collapsed',async({page})=>{
  await page.goto('/workspace');await page.getByRole('button',{name:'Link to clips',exact:true}).click();
  const importer=page.getByRole('region',{name:'Public link to clips',exact:true});
  await expect(importer.locator('.import-customization')).not.toHaveAttribute('open');
  await expect(importer.getByLabel('Clips to generate',{exact:true})).toBeVisible();
  await importer.getByLabel('Import clip length',{exact:true}).selectOption('custom');
  await importer.getByRole('button',{name:'Import Duration 15 to 30 seconds',exact:true}).click();
  await importer.getByLabel('Import Minimum clip duration',{exact:true}).fill('45');
  await expect(importer.getByRole('button',{name:'Get clips',exact:true})).toBeDisabled();
  await importer.getByLabel('Import Minimum clip duration',{exact:true}).fill('15');
  await importer.getByText('Customize clips',{exact:false}).first().click();
  await importer.getByRole('spinbutton',{name:'Clips to generate',exact:true}).fill('7');
  await importer.getByLabel('Video quality',{exact:true}).selectOption('standard');
  await importer.locator('summary').click();
  await expect(importer.locator('summary')).toContainText('7 clips');
  await expect(importer.locator('summary')).toContainText('720p');
  await importer.getByLabel('Public video link',{exact:true}).fill('https://www.youtube.com/watch?v=reference-test');
  await page.route('**/api/source-preview',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({title:'Explicit source metadata fixture',duration:120,platform:'Test source',thumbnail:null,url:'https://www.youtube.com/watch?v=reference-test'})}));
  await page.route('**/api/imports',async route=>{
    expect(route.request().postDataJSON()).toMatchObject({clip_count:7,min_duration:15,max_duration:30,render_quality:'standard',auto_generate:true,auto_render:true});
    await route.fulfill({status:429,contentType:'application/json',body:JSON.stringify({detail:'Please retry shortly.'})});
  });
  await importer.getByRole('button',{name:'Get clips',exact:true}).click();
  await importer.getByRole('button',{name:'Create AI Clips',exact:true}).click();
  await expect(importer.locator('.link-error')).toHaveText('Please retry shortly.');
});

test('Auto quantity submits real analysis and prepares a playable preview without downloading',async({page})=>{
  test.setTimeout(120000);
  execFileSync(backendPython(),['-m','backend.scripts.browser_fixture']);
  await page.request.get('/api/session');await page.goto('/workspace');
  const uploaded=await page.request.post('/api/projects',{multipart:{file:{name:'auto-quantity-test.mp4',mimeType:'video/mp4',buffer:fs.readFileSync('artifacts/browser-fixture.mp4')}}});
  expect(uploaded.status()).toBe(201);const p=await uploaded.json(),base=`/api/projects/${p.id}`;
  let downloads=0;page.on('download',()=>downloads++);
  try{
    await page.request.put(base+'/transcript',{data:[{id:0,start:0,end:3,text:'Why does your audience leave? Because you hide the result, show the solution first and explain one clear lesson.'}]});
    await page.reload();await page.getByRole('button').filter({has:page.getByRole('heading',{name:'auto-quantity-test.mp4',exact:true})}).click();
    await page.getByLabel('Automatic clip quantity',{exact:true}).check();
    await expect(page.getByRole('spinbutton',{name:'Number of clips',exact:true})).toBeDisabled();
    await page.getByLabel('Subtitle script',{exact:true}).selectOption('original');
    await page.getByText('Clip style & export settings',{exact:true}).click();
    await page.getByLabel('Generated quality',{exact:true}).selectOption('fast');
    const response=page.waitForResponse(r=>r.url().endsWith(base+'/highlights')&&r.request().method()==='POST');
    await page.getByRole('button',{name:'Generate AI new clips',exact:true}).click();
    const r=await response;expect(r.request().postDataJSON()).toMatchObject({auto_count:true,clip_count:100});expect(r.status()).toBe(200);
    await expect(page.getByRole('heading',{name:'Rendered clip preview',exact:true})).toBeVisible({timeout:60000});
    const saved=await(await page.request.get(base)).json();expect(saved.clips.length).toBe(1);expect(saved.clip_generation.auto_count).toBeTruthy();
    expect(saved.clip_generation.message).toContain('Short source');expect(saved.media_analysis.waveform.length).toBeGreaterThan(0);
    await expect(page.locator('.workflow-panel>details')).not.toHaveAttribute('open');
    await expect(page.getByRole('link',{name:'Download MP4',exact:true})).toBeVisible();expect(downloads).toBe(0);
    await expect(page.getByRole('region',{name:'Generated clip previews',exact:true})).toBeVisible();
    await page.locator('.review-player video').evaluate(async(video:HTMLVideoElement)=>{await video.play();});
    await expect.poll(()=>page.locator('.review-player video').evaluate((video:HTMLVideoElement)=>video.currentTime)).toBeGreaterThan(0);
    await page.locator('.review-player video').evaluate((video:HTMLVideoElement)=>video.pause());
    await expect(page.getByRole('navigation',{name:'Clipping workflow'}).getByRole('button',{name:'3 Review clips'})).toHaveAttribute('aria-current','step');
    await expect(page.getByRole('region',{name:'Editable clip timeline',exact:true})).toHaveCount(0);
    await page.getByRole('button',{name:'Edit this clip',exact:true}).click();
    await expect(page.getByRole('region',{name:'Editable clip timeline',exact:true})).toBeVisible();
    await page.getByRole('button',{name:'Back to clip previews',exact:true}).click();
    await page.setViewportSize({width:390,height:844});
    await expect(page.getByRole('region',{name:'Selected clip preview',exact:true})).toBeVisible();
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1)).toBeTruthy();
    await page.screenshot({path:'artifacts/clip-review-mobile.png',fullPage:true,animations:'disabled'});
    await page.setViewportSize({width:1440,height:1000});
    await page.screenshot({path:'artifacts/clip-review-desktop.png',fullPage:true,animations:'disabled'});
    page.once('dialog',dialog=>dialog.accept());
    await page.getByRole('button',{name:`Delete ${saved.clips[0].title}`,exact:true}).click();
    await expect.poll(async()=>(await(await page.request.get(base)).json()).clips.length).toBe(0);
  }finally{await page.request.delete(base).catch(()=>{});}
});

test('visual trim, undo redo, timed photo tracks and exported media persist',async({page})=>{
  test.setTimeout(150000);
  const python=backendPython();
  execFileSync(python,['-m','backend.scripts.browser_fixture']);execFileSync(python,['-m','backend.scripts.studio_fixture']);
  await page.request.get('/api/session');await page.goto('/workspace');
  const response=await page.request.post('/api/projects',{multipart:{file:{name:'visual-editor-test.mp4',mimeType:'video/mp4',buffer:fs.readFileSync('artifacts/browser-fixture.mp4')}}});
  expect(response.status()).toBe(201);const p=await response.json(),base=`/api/projects/${p.id}`;
  try{
    await page.request.put(base+'/transcript',{data:[{id:0,start:0,end:3,text:'Why? Because this is a complete test solution.'}]});
    await page.request.post(base+'/highlights',{data:{minimum_score:100,auto_count:true}});
    await page.request.post(base+'/clips',{data:{title:'Visual edit',start:0,end:3,style:'none',render_quality:'fast'}});
    await page.reload();await page.getByRole('button').filter({has:page.getByRole('heading',{name:'visual-editor-test.mp4',exact:true})}).click();
    await page.getByRole('button').filter({has:page.getByText('Visual edit',{exact:true})}).click();
    const timeline=page.getByRole('region',{name:'Editable clip timeline',exact:true});
    await expect(timeline).toBeVisible();await expect(timeline.getByRole('img',{name:'Measured source audio waveform'})).toBeVisible();
    const left=timeline.getByRole('slider',{name:'Trim video start',exact:true});
    await left.scrollIntoViewIfNeeded();const box=await left.boundingBox(),lane=await page.locator('.source-lane').boundingBox();
    await page.mouse.move(box!.x+5,box!.y+10);await page.mouse.down();await page.mouse.move(box!.x+5+lane!.width/6,box!.y+10,{steps:6});await page.mouse.up();
    expect(Number(await left.getAttribute('aria-valuenow'))).toBeCloseTo(.5,1);
    await page.getByRole('button',{name:'Undo clip edit',exact:true}).click();await expect(left).toHaveAttribute('aria-valuenow','0');
    await page.getByRole('button',{name:'Redo clip edit',exact:true}).click();expect(Number(await left.getAttribute('aria-valuenow'))).toBeCloseTo(.5,1);
    await page.getByRole('button',{name:'B-roll & images',exact:true}).click();
    await expect(page.getByLabel('Upload image',{exact:true})).toBeEnabled();
    const upload=page.waitForResponse(r=>r.url().includes('/assets?kind=image')&&r.request().method()==='POST');
    await page.getByLabel('Upload image',{exact:true}).setInputFiles('artifacts/studio-logo.png');expect((await upload).status()).toBe(201);
    await page.getByLabel('Photo start',{exact:true}).fill('0.2');await page.getByLabel('Photo end',{exact:true}).fill('1.2');
    const photo=timeline.getByRole('button',{name:'Move Photo on timeline',exact:true});await photo.focus();await page.keyboard.press('ArrowRight');
    await expect(page.getByLabel('Photo start',{exact:true})).toHaveValue('0.3');await expect(page.getByLabel('Photo end',{exact:true})).toHaveValue('1.3');
    await page.getByRole('button',{name:'Zoom timeline in',exact:true}).click();await page.getByRole('button',{name:'Zoom timeline out',exact:true}).click();
    await page.getByRole('button',{name:'Apply & render',exact:true}).click();
    await expect(page.getByRole('button',{name:'Export ready',exact:true})).toBeVisible({timeout:60000});
    const saved=(await(await page.request.get(base)).json()).clips[0];expect(saved.start).toBeCloseTo(.5,1);expect(saved.image_start).toBe(.3);expect(saved.image_end).toBe(1.3);
    const output=await page.request.get(base+'/media/'+saved.id);expect(output.status()).toBe(200);fs.writeFileSync('artifacts/visual-timeline-export.mp4',await output.body());
    const info=JSON.parse(execFileSync(python,['-c',"from backend import media; import json; print(json.dumps(media.probe('artifacts/visual-timeline-export.mp4')))"],{encoding:'utf8'}));expect(info.duration).toBeCloseTo(2.5,1);expect(info.has_audio).toBeTruthy();
    await page.setViewportSize({width:1600,height:1000});await page.locator('.visual-edit-workspace').screenshot({animations:'disabled',path:'artifacts/visual-editor-desktop.png'});
    for(const width of [1024,768,390]){await page.setViewportSize({width,height:900});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();}
    await timeline.screenshot({animations:'disabled',path:'artifacts/visual-timeline-mobile.png'});
    await page.reload();await page.getByRole('button').filter({has:page.getByRole('heading',{name:'visual-editor-test.mp4',exact:true})}).click();await page.getByRole('button').filter({has:page.getByText('Visual edit',{exact:true})}).click();
    expect(Number(await page.getByRole('slider',{name:'Trim video start',exact:true}).getAttribute('aria-valuenow'))).toBeCloseTo(.5,1);
  }finally{await page.request.delete(base).catch(()=>{});}
});
