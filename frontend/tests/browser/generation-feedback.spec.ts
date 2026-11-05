import {backendPython} from '../backend-python';
import {test,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import path from 'node:path';

const python=backendPython();

test('Generate 100 shows local errors, zero results, an explicit recovery and actual preview',async({page})=>{
  test.setTimeout(120000);
  execFileSync(python,['-m','backend.scripts.browser_fixture']);
  await page.goto('/workspace');
  let downloads=0,requests=0;page.on('download',()=>downloads++);
  const upload=page.waitForResponse(r=>r.url().endsWith('/api/projects')&&r.request().method()==='POST');
  await page.locator('input[type=file]').setInputFiles('artifacts/browser-fixture.mp4');
  const project=await(await upload).json(),base=`/api/projects/${project.id}`;
  try{
    expect((await page.request.put(base+'/transcript',{data:[{id:0,start:0,end:3,text:'Why does your video lose viewers? Because you hide the result, show your audience the solution first and explain the lesson clearly.'}]})).status()).toBe(200);
    await page.reload();
    await page.getByRole('button').filter({has:page.getByRole('heading',{name:'browser-fixture.mp4',exact:true})}).click();
    await page.getByRole('button',{name:'Choose 100 clips',exact:true}).click();
    await page.getByLabel('Minimum engagement score',{exact:true}).fill('100');
    await page.getByText('Clip style & export settings',{exact:true}).click();
    await page.getByLabel('Generated quality',{exact:true}).selectOption('fast');
    page.on('request',r=>{if(r.url().endsWith(base+'/highlights')&&r.method()==='POST')requests++;});
    let release!:()=>void;const gate=new Promise<void>(resolve=>release=resolve);
    await page.route(`**${base}/highlights`,async route=>{await gate;await route.fulfill({status:500,contentType:'text/plain',body:'Internal Server Error'});},{times:1});
    await page.getByRole('button',{name:'Generate 100 new clips',exact:true}).click();
    const feedback=page.getByRole('region',{name:'Clip generation feedback',exact:true});
    try{
      await expect(page.getByRole('button',{name:'Generating clips…',exact:true})).toBeDisabled();
      await expect(feedback).toContainText('Analyzing your saved transcript');
      await expect(page.getByRole('region',{name:'Video processing status',exact:true})).toContainText('Preparing automatic clips');
      expect(requests).toBe(1);
    }finally{release();}
    await expect(feedback.getByRole('alert')).toContainText('HTTP 500');
    await page.getByRole('button',{name:'Generate 100 new clips',exact:true}).click();
    await expect(feedback).toContainText('0 new clips created',{timeout:60000});
    await expect(feedback).toContainText('No new moment passed');
    const recovered=page.waitForResponse(r=>r.url().endsWith(base+'/highlights')&&r.request().method()==='POST');
    await feedback.getByRole('button',{name:'Try Explore all suggestions',exact:true}).click();
    expect((await recovered).request().postDataJSON()).toMatchObject({selection_mode:'all',clip_count:100,auto_render:true});
    await expect(feedback).toContainText('1 new clips created',{timeout:60000});
    await expect(page.getByRole('heading',{name:'Rendered clip preview',exact:true})).toBeVisible({timeout:60000});
    await expect.poll(()=>page.locator('.review-player video').evaluate((v:HTMLVideoElement)=>v.readyState)).toBeGreaterThanOrEqual(1);
    const before=await(await page.request.get(base)).json();
    await feedback.getByRole('button',{name:'Review generated clips',exact:true}).click();
    await expect(page.locator('.batch-toolbar')).toBeInViewport();
    await page.locator('.ai-workflow-summary').click();
    await page.getByRole('button',{name:'Generate 100 new clips',exact:true}).click();
    await expect(feedback).toContainText('already covered by existing clips',{timeout:60000});
    const after=await(await page.request.get(base)).json();
    expect(after.clips).toEqual(before.clips);expect(requests).toBe(4);
    expect(downloads).toBe(0);
    await page.setViewportSize({width:390,height:900});
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
    await feedback.screenshot({animations:'disabled',path:'artifacts/generate-button-mobile.png'});
  }finally{await page.request.delete(base,{timeout:10000}).catch(()=>{});}
});

test('Generate reports a real asynchronous transcription and automatic preview',async({page})=>{
  test.setTimeout(150000);
  execFileSync(python,['-c',"from backend import media; media.run(['-f','lavfi','-i','color=c=0x141925:s=320x180:r=15','-i','data/jfk.flac','-shortest','-c:v','libx264','-c:a','aac','-y','artifacts/generate-speech-fixture.mp4'])"]);
  await page.goto('/workspace');
  const upload=page.waitForResponse(r=>r.url().endsWith('/api/projects')&&r.request().method()==='POST');
  await page.locator('input[type=file]').setInputFiles('artifacts/generate-speech-fixture.mp4');
  const p=await(await upload).json(),base=`/api/projects/${p.id}`;
  try{
    await page.getByLabel('Selection mode',{exact:true}).selectOption('all');
    await page.getByRole('spinbutton',{name:'Number of clips'}).fill('1');
    await page.getByLabel('Subtitle script',{exact:true}).selectOption('original');
    await page.getByLabel('Spoken language',{exact:true}).selectOption('en');
    await page.getByRole('combobox',{name:'Transcription speed',exact:true}).selectOption('fast');
    await page.getByText('Clip style & export settings',{exact:true}).click();
    await page.getByLabel('Generated quality',{exact:true}).selectOption('fast');
    await page.getByRole('button',{name:'Generate 1 new clips',exact:true}).click();
    await expect(page.getByRole('region',{name:'Video processing status',exact:true})).toBeVisible();
    const feedback=page.getByRole('region',{name:'Clip generation feedback',exact:true});
    await expect(feedback).toBeVisible();
    await expect(feedback).toContainText('1 new clips created',{timeout:120000});
    await expect(page.getByRole('heading',{name:'Rendered clip preview',exact:true})).toBeVisible({timeout:60000});
    expect((await(await page.request.get(base)).json()).transcript.map((s:{text:string})=>s.text).join(' ').toLowerCase()).toContain('country');
  }finally{await page.request.delete(base,{timeout:10000}).catch(()=>{});}
});
