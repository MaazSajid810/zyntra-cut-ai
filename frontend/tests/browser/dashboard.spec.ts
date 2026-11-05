import {backendPython} from '../backend-python';
import {test,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import path from 'node:path';
import {readFileSync} from 'node:fs';

test('multi-platform paste-link studio uses the real import endpoint',async({page})=>{
  await page.goto('/workspace');
  await page.getByRole('button',{name:'Link to clips',exact:true}).click();
  const studio=page.getByRole('region',{name:'Public link to clips'});
  await expect(studio.getByRole('heading',{name:'Paste a video link. Get your clips.'})).toBeVisible();
  await studio.locator('.import-customization>summary').click();
  await studio.getByRole('button',{name:'Gaming',exact:false}).click();
  await studio.getByLabel('Clips to generate').fill('12');
  await studio.getByLabel('Import Subtitle script',{exact:true}).selectOption('hindi');
  await studio.getByLabel('Caption font',{exact:true}).selectOption('Righteous');
  // Exercise a handled server rejection without downloading a 20-minute video.
  // Actual download/import is covered by the real public-link test below.
  await page.route('**/api/source-preview',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({title:'Explicit multi-platform metadata fixture',duration:120,platform:'Test source',thumbnail:null,url:route.request().postDataJSON().url})}));
  await page.route('**/api/imports',route=>route.fulfill({status:429,contentType:'application/json',body:JSON.stringify({detail:'Test import limit reached. Retry later.'})}));
  for(const url of ['https://youtu.be/w3tnaCFW_SE','https://www.tiktok.com/@creator/video/123456789','https://www.instagram.com/reel/example/','https://www.facebook.com/reel/123456789','https://example.com/video.mp4']){
    await studio.getByLabel('Public video link').fill(url);
    const posted=page.waitForRequest(r=>r.url().endsWith('/api/imports')&&r.method()==='POST');
    await studio.getByRole('button',{name:'Get clips',exact:true}).click();
    await studio.getByRole('button',{name:'Create AI Clips',exact:true}).click();
    expect((await posted).postDataJSON()).toMatchObject({url,source_kind:'any',caption_script:'hindi',clip_count:12,subtitle_font:'Righteous',style:'yellow',aspect:'vertical',caption_animation:'bounce',auto_generate:true,auto_render:true});
    await expect(studio.locator('.link-error')).toContainText('Test import limit reached');
  }
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
  await page.screenshot({animations:'disabled',path:'artifacts/youtube-studio-mobile.png',fullPage:true});
});

test('two browser guests have private workspaces without login',async({browser})=>{
  const first=await browser.newContext();
  const second=await browser.newContext();
  try{
    await first.request.get('http://127.0.0.1:3000/api/session');
    await second.request.get('http://127.0.0.1:3000/api/session');
    const python=backendPython();
    execFileSync(path.resolve(python),['-m','backend.scripts.browser_fixture']);
    const upload=await first.request.post('http://127.0.0.1:3000/api/projects',{multipart:{file:{name:'private-browser-video.mp4',mimeType:'video/mp4',buffer:readFileSync('artifacts/browser-fixture.mp4')}}});
    expect(upload.status()).toBe(201);
    const project=await upload.json();
    try{
      const a=await first.newPage();const b=await second.newPage();
      await a.goto('http://127.0.0.1:3000/workspace');await b.goto('http://127.0.0.1:3000/workspace');
      await expect(a.getByRole('heading',{name:'private-browser-video.mp4',exact:true})).toBeVisible();
      await expect(b.locator('.sidebar-bottom')).toContainText('Backend connected');
      await expect(b.getByRole('heading',{name:'private-browser-video.mp4',exact:true})).toHaveCount(0);
      expect((await second.request.get('http://127.0.0.1:3000/api/projects')).status()).toBe(200);
      expect(await (await second.request.get('http://127.0.0.1:3000/api/projects')).json()).toEqual([]);
      for(const suffix of ['','/media/source','/media/poster','/subtitles?format=srt']){
        expect((await second.request.get(`http://127.0.0.1:3000/api/projects/${project.id}${suffix}`)).status()).toBe(404);
      }
      expect((await second.request.delete(`http://127.0.0.1:3000/api/projects/${project.id}`)).status()).toBe(404);
      await a.reload();
      await expect(a.getByRole('heading',{name:'private-browser-video.mp4',exact:true})).toBeVisible();
      const cookies=await first.cookies();
      expect(cookies.find(cookie=>cookie.name==='clipforge_guest')?.httpOnly).toBeTruthy();
      expect(cookies.find(cookie=>cookie.name==='clipforge_guest')?.sameSite).toBe('Strict');
      await a.getByRole('button',{name:'My projects',exact:false}).click();
      const deleteButton=a.getByRole('button',{name:'Delete project private-browser-video.mp4',exact:true});
      await expect(deleteButton).toBeVisible();
      await a.setViewportSize({width:390,height:844});
      expect(await a.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
      a.once('dialog',dialog=>dialog.dismiss());
      await deleteButton.click();
      expect((await first.request.get(`http://127.0.0.1:3000/api/projects/${project.id}`)).status()).toBe(200);
      a.once('dialog',dialog=>{expect(dialog.message()).toContain('private-browser-video.mp4');return dialog.accept();});
      const deleted=a.waitForResponse(r=>r.request().method()==='DELETE'&&r.url().endsWith(`/api/projects/${project.id}`));
      await deleteButton.click();
      expect((await deleted).status()).toBe(204);
      await expect(a.getByRole('heading',{name:'private-browser-video.mp4',exact:true})).toHaveCount(0);
      expect((await first.request.get(`http://127.0.0.1:3000/api/projects/${project.id}/media/source`)).status()).toBe(404);
    }finally{expect([204,404]).toContain((await first.request.delete(`http://127.0.0.1:3000/api/projects/${project.id}`)).status());}
  }finally{await first.close();await second.close();}
});

test('dashboard, navigation and mobile layout',async({page})=>{
  await page.goto('/workspace');
  await expect(page.getByRole('heading',{name:'A little footage. Endless possibilities.'})).toBeVisible();
  await page.getByRole('button',{name:'Setup & workflow'}).click();
  const guideDialog=page.getByRole('dialog');
  await expect(guideDialog).toBeVisible();
  await guideDialog.getByRole('button',{name:'Roman Urdu',exact:true}).click();
  await expect(guideDialog.getByRole('heading',{name:'Pehli baar? Apni pehli clip banayen.'})).toBeVisible();
  await expect(guideDialog.getByText('Save, render aur download karein',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Got it'}).click();
  await page.reload();
  const guide=page.getByRole('region',{name:'How to use ZyntraCut AI'});
  await expect(guide.getByRole('button',{name:'Roman Urdu',exact:true})).toHaveAttribute('aria-pressed','true');
  await guide.getByRole('button',{name:'English',exact:true}).click();
  await expect(guide.getByRole('heading',{name:'New here? Make your first clip.'})).toBeVisible();
  expect(await guide.locator('li').count()).toBe(6);
  await expect(guide.getByText(/No login needed/)).toBeVisible();
  await page.getByRole('button',{name:'Exports',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Exports',exact:true}).first()).toBeVisible();
  await page.setViewportSize({width:390,height:844});
  await page.getByRole('button',{name:'Overview',exact:true}).click();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
  await page.screenshot({animations:'disabled',path:'artifacts/dashboard-mobile.png',fullPage:true});
  await page.setViewportSize({width:1440,height:1100});
  await page.screenshot({animations:'disabled',path:'artifacts/dashboard-desktop.png',fullPage:true});
});

test('an inaccessible earlier import does not lock a new guest workspace',async({page})=>{
  await page.addInitScript(()=>localStorage.setItem('clipforge-active-link-import','previous-private-job'));
  await page.goto('/workspace');
  const importer=page.getByRole('region',{name:'Import video from a link'});
  await importer.locator('.import-customization>summary').click();
  await expect(importer.getByRole('alert')).toContainText('unavailable in this guest workspace');
  await importer.getByLabel('Public video link').fill('https://example.com/video.mp4');
  await expect(importer.getByRole('button',{name:'Import & create clips'})).toBeEnabled();
  expect(await page.evaluate(()=>localStorage.getItem('clipforge-active-link-import'))).toBeNull();
});

test('real upload, manual subtitles, render, preview and download',async({page,request})=>{
  const python = backendPython();
  execFileSync(path.resolve(python),['-m','backend.scripts.browser_fixture']);
  await page.goto('/workspace');
  const uploadResponse = page.waitForResponse(r=>r.url().endsWith('/api/projects')&&r.request().method()==='POST');
  await page.locator('input[type=file]').setInputFiles('artifacts/browser-fixture.mp4');
  const uploaded = await uploadResponse;
  expect(uploaded.status()).toBe(201);
  const project = await uploaded.json();
  expect(project.size).toBeGreaterThan(10*1024**2);
  try {
    await expect(page.getByRole('heading',{name:'browser-fixture.mp4',exact:true})).toBeVisible();
    await page.getByRole('button',{name:'Enter a custom clip count'}).click();
    await expect(page.getByRole('spinbutton',{name:'Number of clips'})).toBeFocused();
    await page.getByRole('spinbutton',{name:'Number of clips'}).fill('7');
    await expect(page.getByRole('button',{name:'Generate 7 new clips'})).toBeEnabled();
    await page.getByRole('button',{name:'Choose 30 clips'}).click();
    await expect(page.getByRole('spinbutton',{name:'Number of clips'})).toHaveValue('30');
    await page.getByRole('button',{name:'Choose 100 clips'}).click();
    await expect(page.getByRole('button',{name:'Generate 100 new clips'})).toBeEnabled();
    await page.getByRole('spinbutton',{name:'Number of clips'}).fill('101');
    await expect(page.getByRole('button',{name:'Generate your new clips'})).toBeDisabled();
    await page.getByRole('spinbutton',{name:'Number of clips'}).fill('7');
    await page.getByLabel('Transcription speed').selectOption('fast');
    await page.getByLabel('Prepare generated previews automatically').uncheck();
    await expect(page.getByLabel('Selection mode',{exact:true})).toHaveValue('quality');
    await page.getByLabel('Selection mode',{exact:true}).selectOption('all');
    await page.getByRole('button',{name:'Transcript',exact:false}).filter({hasText:'Transcript'}).click();
    await page.getByRole('button',{name:'Add subtitle'}).click();
    await page.getByRole('textbox',{name:'Subtitle 1',exact:true}).fill('An actual burned-in subtitle');
    await page.getByRole('button',{name:'Save subtitles'}).click();
    await expect(page.getByRole('alert').filter({hasText:'Subtitles saved'})).toBeVisible();
    const generationResponse = page.waitForResponse(r=>r.url().endsWith(`/projects/${project.id}/highlights`)&&r.request().method()==='POST');
    await page.getByRole('button',{name:'Generate 7 new clips'}).click();
    const generation = await generationResponse;
    expect(generation.request().postDataJSON()).toMatchObject({clip_count:7,transcription_mode:'fast',selection_mode:'all',minimum_score:70,auto_render:false});
    expect((await generation.json()).clip_generation.created).toBe(1);
    await expect(page.getByRole('region',{name:'Clip generation feedback',exact:true})).toContainText('Created 1 of 7 requested clips');
    await page.getByRole('button',{name:'New clip',exact:true}).click();
    await page.getByRole('button',{name:'All tools',exact:true}).click();
    await page.getByRole('textbox',{name:'Clip title'}).fill('Browser render verification');
    await page.getByLabel('Voice effect').selectOption('deep');
    await page.getByLabel('Video effect').selectOption('warm');
    for(const style of ['cyan','orange','red','comic','elegant','shadow']){
      await page.getByLabel('Subtitle style').selectOption(style);
      await expect(page.getByLabel('Subtitle style')).toHaveValue(style);
    }
    await page.getByLabel('Subtitle style').selectOption('orange');
    await page.getByLabel('Clip speed',{exact:true}).selectOption('1.2');
    await page.getByLabel('Frame format',{exact:true}).selectOption('portrait');
    await page.getByLabel('Render quality').selectOption('fast');
    await expect(page.getByLabel('Framing',{exact:true})).toHaveValue('fit');
    await page.getByLabel('Framing',{exact:true}).selectOption('crop');
    await page.getByRole('slider',{name:'Horizontal crop position'}).fill('80');
    await page.getByRole('slider',{name:'Vertical crop position'}).fill('20');
    await page.getByLabel('Framing',{exact:true}).selectOption('fit');
    await page.getByRole('checkbox',{name:'Cover creator face / webcam area'}).check();
    await page.getByRole('button',{name:'Top right',exact:true}).click();
    await page.getByRole('slider',{name:'Webcam width',exact:true}).fill('30');
    await page.getByRole('slider',{name:'Webcam height',exact:true}).fill('25');
    await expect(page.getByLabel('Selected webcam cover')).toBeVisible();
    await expect.poll(()=>page.getByLabel('Webcam area source preview').evaluate((video:HTMLVideoElement)=>video.readyState)).toBeGreaterThan(1);
    await page.getByLabel('Subtitle font').selectOption('Poppins');
    await page.getByText('Preview all 11 subtitle fonts',{exact:true}).click();
    await expect(page.getByRole('button',{name:'Your next great clip Poppins · modern'})).toHaveAttribute('aria-pressed','true');
    expect(await page.evaluate(async()=>{const fonts=await document.fonts.load('700 24px Poppins');return fonts.length;})).toBeGreaterThan(0);
    await page.getByLabel('Custom on-screen text').fill('My custom hook');
    await page.getByRole('button',{name:'Create clip',exact:true}).click();
    await page.getByRole('button').filter({has:page.getByRole('heading',{name:'Browser render verification'})}).click();
    await expect(page.getByRole('region',{name:'Apply edits to all clips',exact:true})).toBeVisible();
    const originalRanges=(await(await page.request.get(`/api/projects/${project.id}`)).json()).clips.map((c:{id:string;title:string;start:number;end:number})=>({id:c.id,title:c.title,start:c.start,end:c.end}));
    const applied=page.waitForResponse(r=>r.url().endsWith('/clips/settings')&&r.request().method()==='PUT');
    await page.getByRole('button',{name:'Apply styling to all drafts'}).click();
    const styled=(await (await applied).json()).clips;
    expect(styled.every((clip:{voice_effect:string;overlay_text:string})=>clip.voice_effect==='deep'&&clip.overlay_text==='My custom hook')).toBeTruthy();
    expect(styled.every((clip:{framing:string;crop_x:number;crop_y:number})=>clip.framing==='fit'&&clip.crop_x===80&&clip.crop_y===20)).toBeTruthy();
    expect(styled.every((clip:{hide_webcam:boolean;webcam_x:number;webcam_width:number})=>clip.hide_webcam&&clip.webcam_x===70&&clip.webcam_width===30)).toBeTruthy();
    expect(styled.every((clip:{speed:number;style:string})=>clip.speed===1.2&&clip.style==='orange')).toBeTruthy();
    await page.getByRole('button',{name:'Render all drafts',exact:true}).click();
    await expect(page.getByText('2 / 2 exports ready',{exact:true})).toBeVisible({timeout:60000});
    await expect(page.getByRole('link',{name:'Download MP4'})).toBeVisible({timeout:60000});
    // A playable rendered preview is served inline; generating it never starts
    // a browser download. The explicit Download click below is the only trigger.
    const previewResponse=await page.request.get(`/api/projects/${project.id}/media/${styled[0].id}`);
    expect(previewResponse.headers()['content-disposition']).toContain('inline');
    await expect.poll(()=>page.locator('video:not([aria-label])').evaluate((video:HTMLVideoElement)=>video.readyState)).toBeGreaterThan(0);
    expect(await page.locator('video:not([aria-label])').evaluate((video:HTMLVideoElement)=>video.duration)).toBeCloseTo(2.5,1);
    await page.locator('video:not([aria-label])').evaluate(async(video:HTMLVideoElement)=>{video.muted=true;await video.play();});
    await expect.poll(()=>page.locator('video:not([aria-label])').evaluate((video:HTMLVideoElement)=>video.currentTime)).toBeGreaterThan(.1);
    await page.locator('video:not([aria-label])').evaluate((video:HTMLVideoElement)=>video.pause());
    const downloadEvent = page.waitForEvent('download');
    await page.getByRole('link',{name:'Download MP4'}).click();
    const download = await downloadEvent;
    expect(download.suggestedFilename()).toMatch(/\.mp4$/);
    const previousSrc=await page.locator('video:not([aria-label])').getAttribute('src');
    await page.getByLabel('Video effect').selectOption('vintage');
    await page.getByLabel('Subtitle font').selectOption('Anton');
    const savedFilter=page.waitForResponse(r=>r.url().includes('/clips/')&&r.request().method()==='PUT'&&!r.url().endsWith('/settings'));
    await page.getByRole('button',{name:'Apply & render',exact:true}).click();
    expect((await savedFilter).request().postDataJSON()).toMatchObject({video_effect:'vintage',subtitle_font:'Anton'});
    await expect(page.getByRole('button',{name:'Export ready',exact:true})).toBeVisible({timeout:60000});
    await expect.poll(()=>page.locator('video:not([aria-label])').getAttribute('src')).not.toBe(previousSrc);
    await expect(page.locator('.filter-hint')).toContainText('Included in this rendered export');
    await page.getByLabel('Custom on-screen text').fill('Every clip gets this custom text');
    await page.getByLabel('Call-to-action sticker').selectOption('subscribe');
    await page.getByLabel('Sticker position').selectOption('bottom-right');
    await page.getByLabel('Sticker size',{exact:true}).fill('36');
    await page.getByLabel('Frame format',{exact:true}).selectOption('vertical');
    const bulkUpdate=page.waitForResponse(r=>r.url().includes('/clips/settings?include_ready=true')&&r.request().method()==='PUT');
    await page.getByRole('button',{name:'Apply & render all clips',exact:true}).click();
    const updatedBatch=await bulkUpdate;expect(updatedBatch.status()).toBe(200);
    const batchClips=(await updatedBatch.json()).clips;
    expect(batchClips.every((c:{aspect:string})=>c.aspect==='vertical')).toBeTruthy();
    expect(batchClips.map((c:{id:string;title:string;start:number;end:number})=>({id:c.id,title:c.title,start:c.start,end:c.end}))).toEqual(originalRanges);
    await expect(page.getByText('2 / 2 exports ready',{exact:true})).toBeVisible({timeout:60000});
    await expect.poll(async()=>{
      const allUpdated=(await (await page.request.get(`/api/projects/${project.id}`)).json()).clips;
      return allUpdated.length===2&&allUpdated.every((c:{overlay_text:string;sticker:string;sticker_position:string;sticker_size:number;status:string})=>c.overlay_text==='Every clip gets this custom text'&&c.sticker==='subscribe'&&c.sticker_position==='bottom-right'&&c.sticker_size===36&&c.status==='ready');
    },{timeout:60000}).toBeTruthy();
    // Wait for the editor to receive the completed background renders before
    // editing again; its form remounts as draft/queued/ready status changes.
    await expect(page.getByRole('button',{name:'Export ready',exact:true})).toBeVisible({timeout:60000});
    await expect(page.getByRole('button',{name:'Apply & render all clips',exact:true})).toBeEnabled();
    const srtEvent=page.waitForEvent('download');
    await page.getByRole('link',{name:'Download saved SRT'}).click();
    expect((await srtEvent).suggestedFilename()).toMatch(/\.srt$/);
    await page.getByLabel('Output file').selectOption('webm');
    await page.getByLabel('Clip speed',{exact:true}).selectOption('4');
    await page.getByLabel('Subtitle style').selectOption('elegant');
    await page.getByRole('button',{name:'Save changes',exact:true}).click();
    await page.getByRole('button',{name:'Render video',exact:true}).click();
    await expect(page.getByRole('link',{name:'Download WebM',exact:true})).toBeVisible({timeout:60000});
    await expect.poll(()=>page.locator('video:not([aria-label])').evaluate((video:HTMLVideoElement)=>video.readyState)).toBeGreaterThan(0);
    await expect.poll(()=>page.locator('video:not([aria-label])').evaluate((video:HTMLVideoElement)=>video.duration)).toBeCloseTo(.75,1);
    await page.locator('video:not([aria-label])').evaluate(async(video:HTMLVideoElement)=>{video.muted=true;await video.play();});
    await expect.poll(()=>page.locator('video:not([aria-label])').evaluate((video:HTMLVideoElement)=>video.currentTime)).toBeGreaterThan(.1);
    await page.locator('video:not([aria-label])').evaluate((video:HTMLVideoElement)=>video.pause());
    const webmEvent=page.waitForEvent('download');
    await page.getByRole('link',{name:'Download WebM',exact:true}).click();
    expect((await webmEvent).suggestedFilename()).toMatch(/\.webm$/);
    await page.evaluate(()=>window.scrollTo(0,0));
    await page.screenshot({animations:'disabled',path:'artifacts/editor-desktop.png',fullPage:true});
    await page.setViewportSize({width:390,height:844});
    await page.screenshot({animations:'disabled',path:'artifacts/editor-mobile.png',fullPage:true});
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
    const latest=await (await page.request.get(`/api/projects/${project.id}`)).json();
    const removed=latest.clips.find((clip:{title:string})=>clip.title==='Browser render verification');
    page.once('dialog',dialog=>dialog.accept());
    const deletion=page.waitForResponse(r=>r.request().method()==='DELETE'&&r.url().endsWith(`/clips/${removed.id}`));
    await page.getByRole('button',{name:'Delete this clip',exact:true}).click();
    expect((await deletion).status()).toBe(204);
    await expect(page.getByRole('heading',{name:'Browser render verification',exact:true})).toHaveCount(0);
    expect((await page.request.get(`/api/projects/${project.id}/media/${removed.id}`)).status()).toBe(404);
    expect((await page.request.get(`/api/projects/${project.id}/media/source`)).status()).toBe(200);
    page.once('dialog',dialog=>dialog.accept());
    const projectDeletion=page.waitForResponse(r=>r.request().method()==='DELETE'&&r.url().endsWith(`/api/projects/${project.id}`));
    await page.getByRole('button',{name:'Delete project',exact:true}).click();
    expect((await projectDeletion).status()).toBe(204);
    expect((await page.request.get(`/api/projects/${project.id}`)).status()).toBe(404);
  } finally {
    await page.request.delete(`/api/projects/${project.id}`);
  }
});

test('plain-text upload failures show a useful error and allow retry',async({page})=>{
  await page.route('**/api/projects',async route=>{
    if(route.request().method()==='POST') await route.fulfill({status:500,contentType:'text/plain',body:'Internal Server Error'});
    else await route.continue();
  });
  await page.goto('/workspace');
  await page.locator('input[type=file]').setInputFiles({name:'error-check.mp4',mimeType:'video/mp4',buffer:Buffer.from('error handling fixture')});
  const alert = page.getByRole('alert').filter({hasText:'HTTP 500'});
  await expect(alert).toBeVisible();
  await expect(alert).not.toContainText('Unexpected token');
  await expect(page.getByRole('button',{name:'Upload video',exact:true})).toBeEnabled();
});

test('link import options and blocked local links',async({page})=>{
  await page.goto('/workspace');
  const importer=page.getByRole('region',{name:'Import video from a link'});
  await importer.locator('.import-customization>summary').click();
  await importer.getByLabel('Public video link').fill('http://127.0.0.1/video.mp4');
  await importer.getByLabel('Clips to generate').fill('30');
  await importer.getByLabel('Caption design').selectOption('neon');
  await importer.getByLabel('Import clip speed').selectOption('4');
  for(const quality of ['fast','standard','high']){
    await importer.getByLabel('Video quality',{exact:true}).selectOption(quality);
    await expect(importer.getByLabel('Video quality',{exact:true})).toHaveValue(quality);
  }
  const posted=page.waitForResponse(r=>r.url().endsWith('/api/imports')&&r.request().method()==='POST');
  await importer.getByRole('button',{name:'Import & create clips'}).click();
  const response=await posted;
  expect(response.status()).toBe(400);
  expect(response.request().postDataJSON()).toMatchObject({clip_count:30,style:'neon',speed:4,render_quality:'high',auto_generate:true,auto_render:true});
  await expect(importer.getByRole('alert')).toContainText('private-network');
  await expect(importer.getByRole('button',{name:'Import & create clips'})).toBeEnabled();
});

test('real public link import opens a playable editor',async({page,request})=>{
  test.setTimeout(240000);
  await page.goto('/workspace');
  await page.getByRole('button',{name:'Link to clips',exact:true}).click();
  const importer=page.getByRole('region',{name:'Public link to clips'});
  await importer.locator('.import-customization>summary').click();
  await importer.getByLabel('Public video link').fill('https://www.w3schools.com/html/mov_bbb.mp4');
  await importer.getByLabel('Caption design').selectOption('yellow');
  await importer.getByLabel('Video quality',{exact:true}).selectOption('standard');
  await importer.getByLabel('Caption font',{exact:true}).selectOption('Bebas Neue');
  await importer.getByLabel('Generate captions & clips automatically').uncheck();
  // Metadata inspection is now a separate, real step before video import.
  await importer.getByRole('button',{name:'Import video',exact:true}).click();
  await expect(importer.getByRole('article',{name:'Selected source video',exact:true})).toBeVisible({timeout:60000});
  let releaseImport!:()=>void;
  const importGate=new Promise<void>(resolve=>{releaseImport=resolve;});
  await page.route('**/api/imports',async route=>{const response=await route.fetch();await importGate;await route.fulfill({response});},{times:1});
  const posted=page.waitForResponse(r=>r.url().endsWith('/api/imports')&&r.request().method()==='POST');
  await importer.getByRole('button',{name:'Import video',exact:true}).click();
  try{
    const progress=page.getByRole('region',{name:'Video processing status',exact:true});
    await expect(progress).toContainText('Sending your link');
    await expect(progress).toContainText('Please wait');
    await progress.getByRole('button',{name:'Hide processing status',exact:true}).click();
    await page.getByRole('button',{name:'Show processing status',exact:true}).click();
    await page.setViewportSize({width:390,height:900});
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
    const bounds=await progress.boundingBox();
    expect(bounds!.y).toBeGreaterThanOrEqual(0);
    expect(bounds!.y+bounds!.height).toBeLessThanOrEqual(900);
    await progress.screenshot({path:'artifacts/link-processing-popup-mobile.png',animations:'disabled',timeout:15000});
  }finally{releaseImport();}
  const response=await posted;
  expect(response.status()).toBe(202);
  const job=await response.json();
  let projectId:string|null=null;
  try{
    await expect(page.getByRole('heading',{name:'mov_bbb.mp4',exact:true})).toBeVisible({timeout:210000});
    const finished=await(await page.request.get(`/api/imports/${job.id}`)).json();
    projectId=finished.project_id;
    const project=await(await page.request.get(`/api/projects/${projectId}`)).json();
    expect(project.source_url).toBe('https://www.w3schools.com/html/mov_bbb.mp4');
    expect(project.default_effects.style).toBe('yellow');
    expect(project.default_effects.render_quality).toBe('standard');
    expect(project.default_effects.subtitle_font).toBe('Bebas Neue');
    await page.locator('video:not([aria-label])').evaluate(async(video:HTMLVideoElement)=>{video.muted=true;await video.play();});
    await expect.poll(()=>page.locator('video:not([aria-label])').evaluate((video:HTMLVideoElement)=>video.currentTime)).toBeGreaterThan(.1);
    await page.screenshot({animations:'disabled',path:'artifacts/link-import-editor.png',fullPage:true});
  }finally{
    if(!projectId){const finished=await(await page.request.get(`/api/imports/${job.id}`)).json();projectId=finished.project_id;}
    if(projectId)await page.request.delete(`/api/projects/${projectId}`);
  }
});
