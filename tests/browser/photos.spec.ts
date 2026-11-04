import {test,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import path from 'node:path';
import fs from 'node:fs';

test('oversized B-roll stays local and photos upload, drag and render in both layouts',async({page})=>{
  test.setTimeout(180000);
  const python=path.resolve(process.platform==='win32'?'.venv/Scripts/python.exe':'.venv/bin/python');
  execFileSync(python,['-m','scripts.browser_fixture']);execFileSync(python,['-m','scripts.studio_fixture']);
  const oversized='artifacts/oversized-broll-test.mp4';const fd=fs.openSync(oversized,'w');fs.ftruncateSync(fd,101*1024**2);fs.closeSync(fd);
  await page.goto('/workspace');
  const uploaded=page.waitForResponse(r=>r.url().endsWith('/api/projects')&&r.request().method()==='POST');
  await page.locator('input[type=file]').setInputFiles('artifacts/browser-fixture.mp4');
  const p=await(await uploaded).json(),base=`/api/projects/${p.id}`;
  let release!:()=>void;const gate=new Promise<void>(resolve=>{release=resolve;});
  try{
    await page.request.post(base+'/clips',{data:{title:'Photo test',start:0,end:3,style:'none',render_quality:'fast'}});
    await page.reload();
    await page.getByRole('button').filter({has:page.getByRole('heading',{name:'browser-fixture.mp4',exact:true})}).click();
    await page.getByRole('button').filter({has:page.getByText('Photo test',{exact:true})}).click();
    await page.getByRole('button',{name:'B-roll & images',exact:true}).click();
    let brollPosts=0;page.on('request',request=>{if(request.method()==='POST'&&request.url().includes('/assets?kind=filler'))brollPosts++;});
    await expect(page.getByLabel('Upload filler',{exact:true})).toBeEnabled();
    await page.getByLabel('Upload filler',{exact:true}).setInputFiles(oversized);
    const sizeError=page.getByRole('alert').filter({hasText:'B-roll video is 101.0 MB'});
    await expect(sizeError).toContainText('Maximum: 100 MB');expect(brollPosts).toBe(0);
    await page.getByRole('button',{name:'Branding',exact:true}).click();
    await expect(sizeError).toBeHidden();
    await expect(page.getByLabel('Watermark text',{exact:true})).toBeEnabled();
    await page.getByRole('button',{name:'B-roll & images',exact:true}).click();
    await expect(sizeError).toBeVisible();await page.getByRole('button',{name:'Dismiss filler upload error',exact:true}).click();
    await expect(sizeError).toHaveCount(0);
    // Delay the browser request without reserializing its multipart file body.
    await page.route('**/assets?kind=image',async route=>{await gate;await route.continue();},{times:1});
    const photo=page.waitForResponse(r=>r.url().includes('/assets?kind=image')&&r.request().method()==='POST');
    await page.getByLabel('Upload image',{exact:true}).setInputFiles('artifacts/studio-logo.png');
    await expect(page.getByText('Uploading and validating photo...',{exact:true})).toBeVisible();
    await expect(page.getByRole('button',{name:'Render video',exact:true})).toBeDisabled();
    release();expect((await photo).status()).toBe(201);
    await page.getByLabel('Photo start',{exact:true}).fill('0.5');await page.getByLabel('Photo end',{exact:true}).fill('2.5');
    await page.getByLabel('Photo opacity',{exact:true}).fill('0.6');
    const handle=page.getByRole('button',{name:'Drag photo overlay',exact:true});
    await handle.scrollIntoViewIfNeeded();const box=await handle.boundingBox();
    await page.mouse.move(box!.x+box!.width/2,box!.y+box!.height/2);await page.mouse.down();await page.mouse.move(box!.x+box!.width/2-40,box!.y+box!.height/2,{steps:5});await page.mouse.up();
    expect(Number(await page.getByLabel('Photo X',{exact:true}).inputValue())).toBeLessThan(50);
    await handle.focus();await page.keyboard.press('Shift+ArrowDown');
    expect(Number(await page.getByLabel('Photo Y',{exact:true}).inputValue())).toBe(60);
    await page.getByRole('button',{name:'Apply & render',exact:true}).click();
    await expect(page.getByRole('button',{name:'Export ready',exact:true})).toBeVisible({timeout:60000});
    let saved=(await(await page.request.get(base)).json()).clips[0];
    expect(saved).toMatchObject({image_start:.5,image_end:2.5,image_opacity:.6,image_layout:'overlay'});expect(saved.image_asset_id).toBeTruthy();
    let media=await page.request.get(base+'/media/'+saved.id);expect(media.status()).toBe(200);fs.writeFileSync('artifacts/photo-overlay-browser.mp4',await media.body());
    await page.getByLabel('Photo layout',{exact:true}).selectOption('full');await page.getByLabel('Photo fit',{exact:true}).selectOption('cover');
    await page.getByRole('button',{name:'Apply & render',exact:true}).click();
    await expect(page.getByRole('button',{name:'Export ready',exact:true})).toBeVisible({timeout:60000});
    saved=(await(await page.request.get(base)).json()).clips[0];expect(saved.image_layout).toBe('full');expect(saved.image_fit).toBe('cover');
    media=await page.request.get(base+'/media/'+saved.id);fs.writeFileSync('artifacts/photo-full-browser.mp4',await media.body());
    await expect.poll(()=>page.locator('.video-stage video').evaluate((v:HTMLVideoElement)=>v.readyState)).toBeGreaterThanOrEqual(1);
    for(const width of [1440,768,390]){await page.setViewportSize({width,height:900});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();}
    await page.screenshot({animations:'disabled',path:'artifacts/photo-editor-mobile.png',fullPage:true});
    await page.getByRole('group',{name:'Photo / image overlay',exact:true}).screenshot({animations:'disabled',path:'artifacts/photo-panel-mobile.png'});
  }finally{release();await page.request.delete(base,{timeout:10000}).catch(()=>{});fs.unlinkSync(oversized);}
});
