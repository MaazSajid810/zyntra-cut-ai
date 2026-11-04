import {test,expect,type Page} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import {readFileSync} from 'node:fs';
import path from 'node:path';

async function createProject(page:Page,name:string,titles:string[]){
  await expect(page.locator('.sidebar-bottom')).toContainText('Backend connected');
  const response=await page.request.post('/api/projects',{multipart:{file:{name,mimeType:'video/mp4',buffer:readFileSync('artifacts/browser-fixture.mp4')}}});
  expect(response.status()).toBe(201);
  let project=await response.json();
  for(const title of titles){
    const added=await page.request.post(`/api/projects/${project.id}/clips`,{data:{title,start:0,end:2,style:'none',render_quality:'fast',aspect:'original'}});
    expect(added.status()).toBe(201);project=await added.json();
  }
  return project;
}

test('clip library supports confirmed individual, selected and filtered-all deletion without losing source videos',async({page})=>{
  test.setTimeout(120000);
  execFileSync(path.resolve(process.platform==='win32'?'.venv/Scripts/python.exe':'.venv/bin/python'),['-m','scripts.browser_fixture']);
  await page.goto('/workspace');
  const first=await createProject(page,'library-one.mp4',['Ready alpha','Draft beta','Draft gamma']);
  const second=await createProject(page,'library-two.mp4',['Draft delta','Ready omega']);
  try{
    for(const [project,clip] of [[first,first.clips[0]],[second,second.clips[1]]]){
      expect((await page.request.post(`/api/projects/${project.id}/clips/${clip.id}/render`)).status()).toBe(202);
      await expect.poll(async()=>{const updated=await(await page.request.get(`/api/projects/${project.id}`)).json();return updated.clips.find((c:{id:string})=>c.id===clip.id).status;},{timeout:45000}).toBe('ready');
    }
    await page.reload();await page.getByRole('button',{name:'All clips',exact:true}).click();
    const row=(title:string)=>page.locator('.library-clip').filter({has:page.getByText(title,{exact:true})});
    await expect(page.locator('.library-clip')).toHaveCount(5);
    await expect(row('Ready alpha').getByRole('link',{name:'Download Ready alpha',exact:true})).toBeVisible();
    await page.setViewportSize({width:1440,height:1000});
    await page.screenshot({path:'artifacts/clip-library-desktop.png',fullPage:true,animations:'disabled',timeout:15000});
    page.once('dialog',dialog=>dialog.dismiss());
    await row('Ready alpha').getByRole('button',{name:'Delete clip Ready alpha',exact:true}).click();
    expect((await(await page.request.get(`/api/projects/${first.id}`)).json()).clips).toHaveLength(3);
    await row('Draft beta').getByRole('button',{name:'Open editor',exact:true}).click();
    await expect(page.getByLabel('Clip title',{exact:true})).toHaveValue('Draft beta');
    await page.getByRole('button',{name:'Back to workspace',exact:true}).click();
    page.once('dialog',dialog=>{expect(dialog.message()).toContain('Ready alpha');return dialog.accept();});
    await row('Ready alpha').getByRole('button',{name:'Delete clip Ready alpha',exact:true}).click();
    await expect(page.getByRole('status')).toContainText('1 clip deleted');
    await expect(row('Ready alpha')).toHaveCount(0);
    expect((await page.request.get(`/api/projects/${first.id}/media/${first.clips[0].id}`)).status()).toBe(404);
    await row('Draft beta').getByRole('checkbox').check();await row('Draft delta').getByRole('checkbox').check();
    page.once('dialog',dialog=>{expect(dialog.message()).toContain('2 selected clips');return dialog.accept();});
    await page.getByRole('button',{name:'Delete selected (2)',exact:true}).click();
    await expect(page.getByRole('status')).toContainText('2 clips deleted');
    await expect(page.locator('.library-clip')).toHaveCount(2);
    for(const project of [first,second])expect((await page.request.get(`/api/projects/${project.id}/media/source`)).status()).toBe(200);
    await page.getByRole('button',{name:'Exports',exact:true}).click();
    await expect(page.locator('.library-clip')).toHaveCount(1);
    await page.getByRole('checkbox',{name:'Select all visible clips',exact:true}).check();
    page.once('dialog',dialog=>dialog.accept());
    await page.getByRole('button',{name:'Delete selected (1)',exact:true}).click();
    await expect(page.getByRole('status')).toContainText('1 clip deleted');
    await page.getByRole('button',{name:'All clips',exact:true}).click();
    await page.getByRole('textbox',{name:'Search projects',exact:true}).fill('gamma');
    await page.getByRole('checkbox',{name:'Select all visible clips',exact:true}).check();
    await page.setViewportSize({width:390,height:900});
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
    await page.screenshot({path:'artifacts/clip-library-mobile.png',fullPage:true,animations:'disabled',timeout:15000});
    page.once('dialog',dialog=>dialog.accept());
    await page.getByRole('button',{name:'Delete selected (1)',exact:true}).click();
    await expect(page.locator('.library-clip')).toHaveCount(0);
    for(const project of [first,second]){
      const kept=await page.request.get(`/api/projects/${project.id}`);expect(kept.status()).toBe(200);expect((await kept.json()).clips).toHaveLength(0);
    }
  }finally{await page.request.delete(`/api/projects/${first.id}`);await page.request.delete(`/api/projects/${second.id}`);}
});

test('partial bulk deletion reports failure and keeps failed clips selected for retry',async({page})=>{
  execFileSync(path.resolve(process.platform==='win32'?'.venv/Scripts/python.exe':'.venv/bin/python'),['-m','scripts.browser_fixture']);
  await page.goto('/workspace');
  const project=await createProject(page,'library-retry.mp4',['Keep on failure','Delete successfully']);
  try{
    await page.reload();await page.getByRole('button',{name:'All clips',exact:true}).click();
    const blocked=`/api/projects/${project.id}/clips/${project.clips[0].id}`;
    await page.route(`**${blocked}`,route=>route.fulfill({status:500,contentType:'text/plain',body:'Internal Server Error'}),{times:1});
    await page.getByRole('checkbox',{name:'Select all visible clips',exact:true}).check();
    page.once('dialog',dialog=>dialog.dismiss());
    await page.getByRole('button',{name:'Delete selected (2)',exact:true}).click();
    await expect(page.locator('.library-clip')).toHaveCount(2);
    page.once('dialog',dialog=>dialog.accept());
    await page.getByRole('button',{name:'Delete selected (2)',exact:true}).click();
    await expect(page.getByRole('status')).toContainText('1 clip deleted. 1 could not be deleted');
    await expect(page.getByRole('status')).toContainText('HTTP 500');
    await expect(page.getByRole('checkbox',{name:'Select clip Keep on failure',exact:true})).toBeChecked();
    await expect(page.locator('.library-clip')).toHaveCount(1);
    page.once('dialog',dialog=>dialog.accept());
    await page.getByRole('button',{name:'Delete selected (1)',exact:true}).click();
    await expect(page.getByRole('status')).toContainText('1 clip deleted');
    await expect(page.locator('.library-clip')).toHaveCount(0);
    expect((await page.request.get(`/api/projects/${project.id}/media/source`)).status()).toBe(200);
  }finally{await page.request.delete(`/api/projects/${project.id}`);}
});
