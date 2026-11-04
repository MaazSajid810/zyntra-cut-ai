import {test,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import path from 'node:path';

test('Roman Urdu generation, rendered preview and original-script restoration work',async({page})=>{
  test.setTimeout(180000);
  execFileSync(path.resolve(process.platform==='win32'?'.venv/Scripts/python.exe':'.venv/bin/python'),['-m','scripts.browser_fixture']);
  await page.goto('/workspace');
  let downloads=0;page.on('download',()=>downloads++);
  const imported=page.waitForResponse(r=>r.url().endsWith('/api/projects')&&r.request().method()==='POST');
  await page.locator('input[type=file]').setInputFiles('artifacts/browser-fixture.mp4');
  const p=await(await imported).json(),base=`/api/projects/${p.id}`;
  try{
    // Explicit manual test transcript, not a simulated speech-recognition result.
    expect((await page.request.put(base+'/transcript',{data:[{id:0,start:0,end:3,text:'میں ٹھیک ہوں۔'}]})).status()).toBe(200);
    await page.reload();
    await page.getByRole('button').filter({has:page.getByRole('heading',{name:'browser-fixture.mp4',exact:true})}).click();
    await page.getByLabel('Subtitle script',{exact:true}).selectOption('roman_urdu');
    await expect(page.getByRole('combobox',{name:'Subtitle script',exact:true})).toHaveValue('roman_urdu');
    await page.getByLabel('Selection mode',{exact:true}).selectOption('all');
    await page.getByRole('spinbutton',{name:'Number of clips'}).fill('1');
    await page.getByText('Clip style & export settings',{exact:true}).click();
    await page.getByLabel('Generated quality',{exact:true}).selectOption('fast');
    await page.getByRole('button',{name:'Generate 1 new clips',exact:true}).click();
    await expect(page.getByRole('heading',{name:'Rendered clip preview',exact:true})).toBeVisible({timeout:60000});
    await expect.poll(()=>page.locator('.review-player video').evaluate((v:HTMLVideoElement)=>v.readyState)).toBeGreaterThanOrEqual(1);
    let state=await(await page.request.get(base)).json();
    expect(state.caption_script).toBe('roman_urdu');
    expect(state.transcript[0].text).toBe('main theek hoon.');
    await expect((await page.request.get(base+'/subtitles')).text()).resolves.toContain('main theek hoon.');
    expect(downloads).toBe(0);
    await page.getByRole('button',{name:'Transcript',exact:false}).click();
    await page.getByLabel('Transcript Subtitle script',{exact:true}).selectOption('original');
    page.once('dialog',d=>d.accept());
    await page.getByRole('button',{name:'Apply subtitle script',exact:true}).click();
    await expect(page.getByRole('textbox',{name:'Subtitle 1',exact:true})).toHaveValue('میں ٹھیک ہوں۔');
    state=await(await page.request.get(base)).json();
    expect(state.clips[0].status).toBe('draft');
    expect(state.clips[0].start).toBe(0);expect(state.clips[0].end).toBe(3);
    await page.getByLabel('Transcript Subtitle script',{exact:true}).selectOption('roman_urdu');
    page.once('dialog',d=>d.accept());
    await page.getByRole('button',{name:'Apply subtitle script',exact:true}).click();
    await expect(page.getByRole('textbox',{name:'Subtitle 1',exact:true})).toHaveValue('main theek hoon.');
    await page.getByLabel('Transcript Spoken language',{exact:true}).selectOption('ur');
    for(const width of [1440,768,390]){
      await page.setViewportSize({width,height:900});
      expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
    }
    await page.evaluate(()=>window.scrollTo(0,0));
    await page.screenshot({animations:'disabled',path:'artifacts/roman-urdu-mobile.png',fullPage:true});
  }finally{await page.request.delete(base,{timeout:10000}).catch(()=>{});}
});
