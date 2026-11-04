import {test,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import path from 'node:path';

test('English speech can generate real Urdu captions independently of spoken language',async({page})=>{
  test.setTimeout(240000);
  execFileSync(path.resolve(process.platform==='win32'?'.venv/Scripts/python.exe':'.venv/bin/python'),['-c',"from backend import media; media.run(['-f','lavfi','-i','color=c=0x141925:s=320x180:r=15','-i','data/jfk.flac','-shortest','-c:v','libx264','-c:a','aac','artifacts/translation-browser-source.mp4'])"]);
  await page.goto('/workspace');
  let downloads=0;page.on('download',()=>downloads++);
  const uploaded=page.waitForResponse(r=>r.url().endsWith('/api/projects')&&r.request().method()==='POST');
  await page.locator('input[type=file]').setInputFiles('artifacts/translation-browser-source.mp4');
  const p=await(await uploaded).json(),base=`/api/projects/${p.id}`;
  try{
    await page.getByLabel('Subtitle script',{exact:true}).selectOption('urdu');
    await page.getByLabel('Spoken language',{exact:true}).selectOption('en');
    await expect(page.getByLabel('Subtitle script',{exact:true})).toHaveValue('urdu');
    await page.getByLabel('Selection mode',{exact:true}).selectOption('all');
    await page.getByRole('spinbutton',{name:'Number of clips'}).fill('1');
    await page.getByLabel('Transcription speed',{exact:true}).selectOption('fast');
    await page.getByText('Clip style & export settings',{exact:true}).click();
    await page.getByLabel('Generated quality',{exact:true}).selectOption('fast');
    await page.getByRole('button',{name:'Generate 1 new clips',exact:true}).click();
    await expect(page.getByRole('region',{name:'Video processing status',exact:true})).toBeVisible();
    await expect(page.getByRole('heading',{name:'Rendered clip preview',exact:true})).toBeVisible({timeout:180000});
    const saved=await(await page.request.get(base)).json();
    expect(saved.language).toBe('en');expect(saved.caption_script).toBe('urdu');
    expect(saved.transcript[0].text).toMatch(/[\u0600-\u06ff]/);expect(saved.transcript[0].text).not.toContain('▁');
    expect(saved.transcript[0].words).toBeUndefined();expect(saved.transcript[0].source_text).toMatch(/Americans/i);
    await page.getByRole('button',{name:'Transcript',exact:false}).click();
    await expect(page.locator('.translation-source').first()).toContainText('Original:');
    await expect(page.getByLabel('Transcript Spoken language',{exact:true})).toHaveValue('en');
    await expect(page.getByLabel('Transcript Spoken language',{exact:true})).toBeEnabled();
    await page.setViewportSize({width:390,height:900});
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
    await page.screenshot({animations:'disabled',path:'artifacts/translation-review-mobile.png',fullPage:true});
    expect(downloads).toBe(0);
  }finally{await page.request.delete(base,{timeout:10000}).catch(()=>{});}
});
