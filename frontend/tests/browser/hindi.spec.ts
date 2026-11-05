import {backendPython} from '../backend-python';
import {test,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import path from 'node:path';

test('Hindi captions render for preview and switch to Roman Urdu and back',async({page})=>{
  test.setTimeout(120000);
  execFileSync(backendPython(),['-m','backend.scripts.browser_fixture']);
  await page.goto('/workspace');
  let downloads=0;page.on('download',()=>downloads++);
  const uploaded=page.waitForResponse(r=>r.url().endsWith('/api/projects')&&r.request().method()==='POST');
  await page.locator('input[type=file]').setInputFiles('artifacts/browser-fixture.mp4');
  const project=await(await uploaded).json(),base=`/api/projects/${project.id}`;
  try{
    // Manual Hindi fixture; actual Hindi speech recognition has a separate test.
    expect((await page.request.put(base+'/transcript',{data:[{id:0,start:0,end:3,text:'मैं ठीक हूँ।'}]})).status()).toBe(200);
    await page.reload();
    await page.getByRole('button').filter({has:page.getByRole('heading',{name:'browser-fixture.mp4',exact:true})}).click();
    await page.getByLabel('Subtitle script',{exact:true}).selectOption('hindi');
    // Output language must never silently change the source speech language.
    await expect(page.getByLabel('Spoken language',{exact:true})).toHaveValue('auto');
    await expect(page.getByLabel('Transcription speed')).toContainText('small model');
    await page.getByLabel('Selection mode',{exact:true}).selectOption('all');
    await page.getByRole('spinbutton',{name:'Number of clips'}).fill('1');
    await page.getByText('Clip style & export settings',{exact:true}).click();
    await page.getByLabel('Generated quality',{exact:true}).selectOption('fast');
    await page.getByRole('button',{name:'Generate 1 new clips',exact:true}).click();
    await expect(page.getByRole('heading',{name:'Rendered clip preview',exact:true})).toBeVisible({timeout:60000});
    await expect.poll(()=>page.locator('.review-player video').evaluate((v:HTMLVideoElement)=>v.readyState)).toBeGreaterThanOrEqual(1);
    let p=await(await page.request.get(base)).json();
    expect(p.caption_script).toBe('hindi');expect(p.transcript[0].text).toBe('मैं ठीक हूँ।');
    expect(await(await page.request.get(base+'/subtitles')).text()).toContain('मैं ठीक हूँ।');
    expect(await(await page.request.get(base+'/subtitles?format=vtt')).text()).toContain('मैं ठीक हूँ।');
    expect(downloads).toBe(0);
    await page.getByRole('button',{name:'Transcript',exact:false}).click();
    await page.getByLabel('Transcript Subtitle script',{exact:true}).selectOption('roman_urdu');
    page.once('dialog',d=>d.accept());
    await page.getByRole('button',{name:'Apply subtitle script',exact:true}).click();
    await expect(page.getByRole('textbox',{name:'Subtitle 1',exact:true})).toHaveValue('main theek hoon.');
    await page.getByLabel('Transcript Subtitle script',{exact:true}).selectOption('hindi');
    page.once('dialog',d=>d.accept());
    await page.getByRole('button',{name:'Apply subtitle script',exact:true}).click();
    await expect(page.getByRole('textbox',{name:'Subtitle 1',exact:true})).toHaveValue('मैं ठीक हूँ।');
    p=await(await page.request.get(base)).json();
    expect(p.clips[0].status).toBe('draft');expect(p.clips[0].start).toBe(0);expect(p.clips[0].end).toBe(3);
    for(const width of [1440,768,390]){
      await page.setViewportSize({width,height:900});
      expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
    }
    await page.locator('.transcript-language-controls').screenshot({animations:'disabled',path:'artifacts/hindi-controls-mobile.png'});
  }finally{await page.request.delete(base,{timeout:10000}).catch(()=>{});}
});
