import {test,expect} from '@playwright/test';

test('project polling clears recovered connection errors while preserving upload rejections',async({page})=>{
  let disconnected=true,successfulReads=0;
  await page.route('**/api/projects',async route=>{
    if(route.request().method()==='POST'){
      // Explicit action-error fixture; no file is stored or processed.
      await route.fulfill({status:400,contentType:'application/json',body:JSON.stringify({detail:'Explicit upload rejection fixture'})});
    }else if(disconnected){await route.abort('connectionfailed');}
    else{const response=await route.fetch();successfulReads++;await route.fulfill({response});}
  });
  await page.goto('/dashboard');
  const alert=page.locator('.platform-main>.platform-alert');
  await expect(alert).toContainText('Connection to the app was interrupted');
  await expect(alert).not.toContainText('Failed to fetch');
  await expect(page.getByRole('complementary',{name:'Workspace sections'}).getByRole('link',{name:'Full editor',exact:true})).toHaveCount(0);
  disconnected=false;
  await expect(alert).toHaveCount(0,{timeout:12000});
  await page.locator('input[type=file]').setInputFiles({name:'rejected.mp4',mimeType:'video/mp4',buffer:Buffer.from('Explicit rejected-upload fixture')});
  await expect(alert).toContainText('Explicit upload rejection fixture');
  const before=successfulReads;
  await expect.poll(()=>successfulReads,{timeout:12000}).toBeGreaterThan(before);
  await expect(alert).toContainText('Explicit upload rejection fixture');
});

test('a dropped import POST is explained and only resubmitted by an explicit click',async({page})=>{
  let posts=0;
  // Metadata and rejection are deliberate UI fixtures, not successful imports.
  await page.route('**/api/source-preview',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({title:'Connection recovery fixture',duration:120,thumbnail:null,platform:'Test source',url:'https://example.com/video.mp4'})}));
  await page.route('**/api/imports',async route=>{
    posts++;
    if(posts===1)await route.abort('connectionfailed');
    else await route.fulfill({status:429,contentType:'application/json',body:JSON.stringify({detail:'Explicit retry rejection fixture'})});
  });
  await page.goto('/dashboard');
  await page.getByLabel('Public video link',{exact:true}).fill('https://example.com/video.mp4');
  await page.getByRole('button',{name:'Get clips',exact:true}).click();
  await expect(page.getByRole('article',{name:'Selected source video',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Create AI Clips',exact:true}).click();
  await expect(page.locator('.link-error')).toContainText('Connection to the app was interrupted');
  await expect(page.locator('.link-error')).toContainText('check Library');
  await expect(page.getByRole('button',{name:'Create AI Clips',exact:true})).toBeEnabled();
  // Advance past the import poll interval; a failed POST must not be replayed.
  await page.clock.install();await page.clock.fastForward(3000);
  expect(posts).toBe(1);
  await expect(page.getByLabel('Public video link',{exact:true})).toHaveValue('https://example.com/video.mp4');
  await page.getByRole('button',{name:'Create AI Clips',exact:true}).click();
  await expect(page.locator('.link-error')).toContainText('Explicit retry rejection fixture');
  expect(posts).toBe(2);
});

test('an accepted import resumes status polling after a disconnect without creating another job',async({page})=>{
  let disconnected=true,posts=0;
  // Status-only fixture represents an already accepted job; no AI output is mocked.
  await page.addInitScript(()=>localStorage.setItem('clipforge-active-link-import','connection-recovery-fixture'));
  await page.route('**/api/imports/connection-recovery-fixture',async route=>{
    if(disconnected)await route.abort('connectionfailed');
    else await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({id:'connection-recovery-fixture',status:'queued',progress:0,downloaded_bytes:0,error:null,project_id:null,message:'Explicit connected job-status fixture',options:{url:'https://example.com/existing.mp4'}})});
  });
  await page.route('**/api/imports',async route=>{posts++;await route.fulfill({status:500,body:'Unexpected duplicate import'});});
  await page.goto('/dashboard');
  await expect(page.locator('.link-error')).toContainText('Connection to the app was interrupted');
  disconnected=false;
  await expect(page.locator('.link-error')).toHaveCount(0,{timeout:10000});
  await expect(page.getByRole('region',{name:'Video processing status',exact:true})).toContainText('Explicit connected job-status fixture');
  expect(await page.evaluate(()=>localStorage.getItem('clipforge-active-link-import'))).toBe('connection-recovery-fixture');
  expect(posts).toBe(0);
});
