import {backendPython} from '../backend-python';
import {test,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import path from 'node:path';

test('generate prepares a preview then supports scheduled stickers, voice comparison and clip deletion',async({page})=>{
  test.setTimeout(150000);
  execFileSync(backendPython(),['-m','backend.scripts.browser_fixture']);
  await page.goto('/workspace');
  let downloads=0;page.on('download',()=>downloads++);
  const upload=page.waitForResponse(r=>r.url().endsWith('/api/projects')&&r.request().method()==='POST');
  await page.locator('input[type=file]').setInputFiles('artifacts/browser-fixture.mp4');
  const p=await(await upload).json(),base=`/api/projects/${p.id}`;
  try{
    expect((await page.request.put(base+'/transcript',{data:[{id:0,start:0,end:3,text:'An actual automatic preview test.'}]})).status()).toBe(200);
    await page.reload();
    await page.getByRole('button').filter({has:page.getByRole('heading',{name:'browser-fixture.mp4',exact:true})}).click();
    await page.getByLabel('Selection mode',{exact:true}).selectOption('all');
    await expect(page.getByLabel('Prepare generated previews automatically')).toBeChecked();
    await page.getByRole('spinbutton',{name:'Number of clips'}).fill('1');
    await page.getByText('Clip style & export settings',{exact:true}).click();
    await page.getByLabel('Generated quality',{exact:true}).selectOption('fast');
    await page.getByLabel('Generated voice',{exact:true}).selectOption('deep');
    await page.getByLabel('Generated frame format',{exact:true}).selectOption('vertical');
    await page.getByRole('button',{name:'Generate 1 new clips',exact:true}).click();
    await expect(page.getByRole('heading',{name:'Rendered clip preview',exact:true})).toBeVisible({timeout:60000});
    await page.getByRole('button',{name:'Edit this clip',exact:true}).click();
    await page.getByRole('button',{name:'Audio & sound effects',exact:true}).click();
    await expect(page.getByLabel('Voice strength',{exact:true})).toBeVisible();
    await expect(page.getByLabel('Subtitle font',{exact:true})).toBeHidden();
    await page.getByRole('button',{name:'Frame & trim',exact:true}).click();
    await expect(page.getByLabel('Trim start',{exact:true})).toBeVisible();
    await page.getByRole('button',{name:'Captions',exact:true}).click();
    await expect(page.getByLabel('Subtitle font',{exact:true})).toBeVisible();
    await page.evaluate(()=>window.scrollTo(0,0));
    const preview=await page.locator('.clip-preview-workspace').boundingBox();
    const properties=await page.locator('.clip-properties').boundingBox();
    const timeline=await page.locator('.visual-timeline').boundingBox();
    expect(properties!.x).toBeGreaterThanOrEqual(preview!.x+preview!.width);
    expect(timeline!.y).toBeGreaterThanOrEqual(Math.max(preview!.y+preview!.height,properties!.y+properties!.height));
    await page.screenshot({animations:'disabled',path:'artifacts/reference-editor-desktop.png',fullPage:true});
    await page.getByRole('button',{name:'All tools',exact:true}).click();
    expect(downloads).toBe(0);
    for(const [name,font] of [['High energy','Anton'],['Podcast','Poppins'],['Gaming','Bangers'],['Cinematic','Anton'],['Educational','Poppins'],['Minimal','Poppins'],['Reaction','Bangers']]){
      await page.getByRole('button',{name,exact:true}).click();
      await expect(page.getByLabel('Subtitle font',{exact:true})).toHaveValue(font);
    }
    await page.getByLabel('Motion zoom',{exact:true}).selectOption('none');
    for(const voice of ['radio','echo','mute','none','high','deep'])await page.getByLabel('Voice effect',{exact:true}).selectOption(voice);
    await page.getByLabel('Call-to-action sticker',{exact:true}).selectOption('follow');
    for(const timing of ['start','middle','custom'])await page.getByLabel('Sticker timing',{exact:true}).selectOption(timing);
    await page.getByLabel('Sticker starts at',{exact:true}).fill('0.1');
    await page.getByLabel('Sticker timing',{exact:true}).selectOption('end');
    for(const animation of ['slide','fade','none'])await page.getByLabel('Sticker animation',{exact:true}).selectOption(animation);
    await page.getByLabel('Sticker animation',{exact:true}).selectOption('pop');
    await page.getByLabel('Sticker duration',{exact:true}).fill('0.6');
    await page.getByLabel('Voice strength',{exact:true}).fill('0.9');
    await page.getByLabel('Cover burned-in source captions',{exact:true}).check();
    await page.getByLabel('Source caption band height',{exact:true}).fill('20');
    const saved=page.waitForResponse(r=>r.request().method()==='PUT'&&r.url().includes('/clips/'));
    await page.getByRole('button',{name:'Apply & render',exact:true}).click();
    expect((await saved).request().postDataJSON()).toMatchObject({sticker:'follow',sticker_enabled:true,sticker_timing:'end',sticker_animation:'pop',sticker_duration:.6,voice_strength:.9,cover_source_captions:true,source_caption_height:20});
    await expect(page.getByRole('button',{name:'Export ready',exact:true})).toBeVisible({timeout:60000});
    await page.getByText('Compare original and rendered audio',{exact:true}).click();
    const audio=page.getByLabel('Rendered clip audio',{exact:true});
    await audio.evaluate(async(a:HTMLAudioElement)=>{a.muted=true;await a.play();});
    await expect.poll(()=>audio.evaluate((a:HTMLAudioElement)=>a.currentTime)).toBeGreaterThan(.1);
    await audio.evaluate((a:HTMLAudioElement)=>a.pause());
    for(const width of [1440,1024,768,390]){
      await page.setViewportSize({width,height:900});
      expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
    }
    expect(await page.locator('button button').count()).toBe(0);
    expect(await page.evaluate(()=>{const ids=[...document.querySelectorAll('[id]')].map(el=>el.id);return ids.length===new Set(ids).size;})).toBeTruthy();
    await page.screenshot({animations:'disabled',path:'artifacts/final-editor-mobile.png',fullPage:true});
    expect(downloads).toBe(0);
    const chosen=(await(await page.request.get(base)).json()).clips[0];
    page.once('dialog',dialog=>dialog.dismiss());
    await page.getByRole('button',{name:'Delete this clip',exact:true}).click();
    expect((await page.request.get(base+'/media/'+chosen.id)).status()).toBe(200);
    page.once('dialog',dialog=>dialog.accept());
    const deleted=page.waitForResponse(r=>r.request().method()==='DELETE'&&r.url().endsWith('/clips/'+chosen.id));
    await page.getByRole('button',{name:'Delete this clip',exact:true}).click();
    expect((await deleted).status()).toBe(204);
    expect((await page.request.get(base+'/media/'+chosen.id)).status()).toBe(404);
    expect((await page.request.get(base+'/media/source')).status()).toBe(200);
  }finally{await page.request.delete(base,{timeout:10000}).catch(()=>{});}
});
