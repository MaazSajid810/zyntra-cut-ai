import {backendPython} from '../backend-python';
import {test,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import {readFileSync} from 'node:fs';
import path from 'node:path';

test('quality first rejects weak candidates and previews approved clips without automatic downloads',async({page})=>{
  test.setTimeout(120000);
  const python=backendPython();
  execFileSync(python,['-c',"from backend import media; media.run(['-f','lavfi','-i','testsrc2=size=320x180:rate=10','-t','24','-c:v','libx264','-pix_fmt','yuv420p','artifacts/quality-fixture.mp4'])"]);
  expect((await page.request.get('/api/session')).status()).toBe(200);
  await page.goto('/workspace');
  let downloads=0;
  page.on('download',()=>downloads++);
  const uploaded=await page.request.post('/api/projects',{multipart:{file:{name:'quality-test-only.mp4',mimeType:'video/mp4',buffer:readFileSync('artifacts/quality-fixture.mp4')}}});
  expect(uploaded.status()).toBe(201);
  const project=await uploaded.json();
  const base=`/api/projects/${project.id}`;
  try{
    const transcript=[
      {id:0,start:0,end:8,text:'Why does your video lose every viewer in the first three seconds? Here is the mistake you can fix.'},
      {id:1,start:8,end:16,text:'The solution is to show the result first because your audience needs a reason to keep watching.'},
      {id:2,start:16,end:24,text:'Finally remove the long introduction and give your audience one clear lesson they can use today.'},
    ];
    expect((await page.request.put(`${base}/transcript`,{data:transcript})).status()).toBe(200);
    await page.reload();
    await page.getByRole('button').filter({has:page.getByRole('heading',{name:'quality-test-only.mp4',exact:true})}).click();
    await page.getByLabel('Prepare generated previews automatically').uncheck();
    await expect(page.getByLabel('Selection mode',{exact:true})).toHaveValue('quality');
    await page.getByLabel('Minimum engagement score',{exact:true}).fill('100');
    await page.getByRole('button',{name:'Generate 5 new clips',exact:true}).click();
    await expect(page.getByRole('region',{name:'Clip generation feedback',exact:true})).toContainText('Created 0 of up to 5',{timeout:60000});
    await page.getByLabel('Minimum engagement score',{exact:true}).fill('70');
    await page.getByRole('button',{name:'Generate 5 new clips',exact:true}).click();
    await expect(page.getByRole('region',{name:'Clip generation feedback',exact:true})).toContainText('Created 1 of up to 5',{timeout:60000});
    await page.getByRole('button',{name:'Edit this clip',exact:true}).click();
    await expect(page.getByRole('heading',{name:'Why this moment?',exact:true})).toBeVisible();
    await expect(page.locator('.selection-evidence')).toContainText('Visual changes sampled at 2 fps');
    await page.getByRole('button',{name:'All tools',exact:true}).click();
    const chosen=(await (await page.request.get(base)).json()).clips[0];
    let releaseRender!:()=>void;
    const responseGate=new Promise<void>(resolve=>{releaseRender=resolve;});
    await page.route(`**${base}/clips/${chosen.id}/render`,async route=>{
      const response=await route.fetch();
      await responseGate;
      await route.fulfill({response});
    },{times:1});
    try{
      await page.getByRole('button',{name:'Render video',exact:true}).click();
      await expect(page.getByLabel('Subtitle font',{exact:true})).toBeDisabled();
      await expect(page.getByLabel('Video effect',{exact:true})).toBeDisabled();
      await expect(page.getByLabel('Frame format',{exact:true})).toBeDisabled();
    }finally{releaseRender();}
    await expect(page.getByRole('heading',{name:'Rendered clip preview',exact:true})).toBeVisible({timeout:60000});
    const video=page.locator('.video-stage video');
    await expect.poll(()=>video.evaluate((v:HTMLVideoElement)=>v.readyState)).toBeGreaterThan(1);
    await video.evaluate(async(v:HTMLVideoElement)=>{v.muted=true;await v.play();});
    await expect.poll(()=>video.evaluate((v:HTMLVideoElement)=>v.currentTime)).toBeGreaterThan(.1);
    await video.evaluate((v:HTMLVideoElement)=>v.pause());
    expect(downloads).toBe(0);
    const event=page.waitForEvent('download');
    await page.getByRole('link',{name:'Download MP4',exact:true}).click();
    expect((await event).suggestedFilename()).toMatch(/\.mp4$/);
    expect(downloads).toBe(1);
    // A draft range beginning later in the source must seek to its own start.
    expect((await page.request.post(`${base}/clips`,{data:{title:'Later preview range',start:6,end:9}})).status()).toBe(201);
    await page.getByRole('button').filter({has:page.getByRole('heading',{name:'Later preview range',exact:true})}).click();
    await expect(page.getByRole('heading',{name:'Source range preview',exact:true})).toBeVisible();
    await expect.poll(()=>video.evaluate((v:HTMLVideoElement)=>v.currentTime)).toBeCloseTo(6,0);
    await page.setViewportSize({width:390,height:844});
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
  }finally{await page.request.delete(base);}
});
