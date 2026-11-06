import {test,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import {readFileSync} from 'node:fs';
import {backendPython} from '../backend-python';

test('full-screen reels follow a real face, crop old captions and apply to all clips',async({page})=>{
  execFileSync(backendPython(),['-c',[
    'from pathlib import Path',
    'from PIL import Image, ImageDraw',
    'from backend import media',
    "p=Path('artifacts');p.mkdir(exist_ok=True)",
    "image=Image.new('RGB',(640,360),(70,110,150))",
    "image.paste(Image.open('backend/tests/fixtures/nasa-astronaut-face.png'),(220,30))",
    "ImageDraw.Draw(image).rectangle((0,288,640,360),fill=(220,15,15))",
    "image.save(p/'reel-browser-source.png')",
    "media.run(['-loop','1','-i',str(p/'reel-browser-source.png'),'-t','3','-r','12','-c:v','libx264','-pix_fmt','yuv420p',str(p/'reel-browser-source.mp4')])",
  ].join('\n')]);
  await page.request.get('/api/session');
  await page.goto('/dashboard');
  await expect(page.getByLabel('Import aspect ratio',{exact:true})).toHaveValue('vertical');
  await expect(page.getByLabel('Import framing',{exact:true})).toHaveValue('follow');
  const upload=await page.request.post('/api/projects',{multipart:{file:{name:'Public NASA reel fixture.mp4',mimeType:'video/mp4',buffer:readFileSync('artifacts/reel-browser-source.mp4')}}});
  expect(upload.status()).toBe(201);
  const project=await upload.json(),base='/api/projects/'+project.id;
  expect(project.default_effects).toMatchObject({aspect:'vertical',framing:'follow'});
  let downloads=0;page.on('download',()=>downloads++);
  try{
    expect((await page.request.put(base+'/transcript',{data:[{id:0,start:0,end:3,text:'A full screen reel.'}]})).status()).toBe(200);
    for(const [title,start,end] of [['First reel',0,2],['Second reel',1,3]]){
      expect((await page.request.post(base+'/clips',{data:{title,start,end,style:'clean',render_quality:'fast',aspect:'vertical',framing:'fit'}})).status()).toBe(201);
    }
    const original=(await(await page.request.get(base)).json()).clips;
    await page.goto(`/editor?project=${project.id}&clip=${original[0].id}`);
    await page.getByRole('button',{name:'Frame & trim',exact:true}).click();
    await expect(page.getByLabel('Framing',{exact:true})).toHaveValue('fit');
    await page.getByRole('button',{name:'Full-screen 9:16 reel',exact:true}).click();
    await expect(page.getByLabel('Framing',{exact:true})).toHaveValue('follow');
    await page.getByRole('button',{name:'Remove old captions & fill reel',exact:true}).click();
    await expect(page.getByLabel('Old caption treatment',{exact:true})).toHaveValue('crop_bottom');
    await page.getByLabel('Old caption edge crop',{exact:true}).fill('20');
    const batch=page.waitForResponse(r=>r.url().includes('/clips/settings?include_ready=true')&&r.request().method()==='PUT');
    await page.getByRole('button',{name:'Apply & render all clips',exact:true}).click();
    expect((await batch).status()).toBe(200);
    await expect.poll(async()=>{
      const p=await(await page.request.get(base)).json();
      return p.clips.every((c:any)=>c.status==='ready'&&c.framing==='follow'&&c.source_caption_method==='crop_bottom'&&c.framing_analysis.detected>0);
    },{timeout:60000}).toBeTruthy();
    const clips=(await(await page.request.get(base)).json()).clips;
    expect(clips.map((c:any)=>[c.id,c.start,c.end])).toEqual(original.map((c:any)=>[c.id,c.start,c.end]));
    await expect(page.getByRole('button',{name:'Export ready',exact:true})).toBeVisible({timeout:60000});
    const video=page.locator('.clip-preview-workspace video');
    await expect.poll(()=>video.evaluate((v:HTMLVideoElement)=>[v.videoWidth,v.videoHeight])).toEqual([480,854]);
    const stage=await page.locator('.clip-preview-workspace .video-stage').boundingBox();
    expect(stage!.width/stage!.height).toBeCloseTo(9/16,2);
    await expect(page.locator('.clip-preview-workspace')).toContainText('Following a visible face');
    await video.evaluate(async(v:HTMLVideoElement)=>{v.muted=true;await v.play();});
    await expect.poll(()=>video.evaluate((v:HTMLVideoElement)=>v.currentTime)).toBeGreaterThan(.1);
    await video.evaluate((v:HTMLVideoElement)=>v.pause());
    expect(downloads).toBe(0);
    for(const width of [1440,390]){
      await page.setViewportSize({width,height:1000});
      expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
      await page.screenshot({path:`artifacts/reel-editor-${width}.png`,fullPage:true,animations:'disabled'});
    }
  }finally{
    await page.goto('about:blank'); // Release the Windows video-file handle before deletion.
    await expect.poll(async()=>[204,404].includes((await page.request.delete(base)).status()),{timeout:15000}).toBeTruthy();
  }
});
