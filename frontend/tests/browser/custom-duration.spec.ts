import {backendPython} from '../backend-python';
import {test,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

test('custom count and duration create actual bounded MP4 clips and persist after reopening',async({page})=>{
  test.setTimeout(150000);
  const python=backendPython();
  execFileSync(python,['-c',"from backend import media; media.run(['-f','lavfi','-i','testsrc2=size=160x90:rate=10','-f','lavfi','-i','sine=frequency=440:sample_rate=16000','-t','24','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','artifacts/custom-duration-source.mp4'])"]);
  await page.request.get('/api/session');await page.goto('/workspace');
  const uploaded=await page.request.post('/api/projects',{multipart:{file:{name:'custom-duration-test.mp4',mimeType:'video/mp4',buffer:fs.readFileSync('artifacts/custom-duration-source.mp4')}}});
  expect(uploaded.status()).toBe(201);const p=await uploaded.json(),base=`/api/projects/${p.id}`;
  try{
    // Explicit manual transcript fixture; this scenario tests selection/export, not recognition accuracy.
    await page.request.put(base+'/transcript',{data:['camera settings','podcast microphones','travel budgets'].map((topic,i)=>({id:i,start:i*8,end:(i+1)*8,text:`Why improve ${topic}? Because this solution saves your audience time and teaches a useful lesson.`}))});
    await page.reload();await page.getByRole('button').filter({has:page.getByRole('heading',{name:p.name,exact:true})}).click();
    await page.getByLabel('Number of clips',{exact:true}).fill('2');
    await page.getByLabel('Minimum clip duration',{exact:true}).fill('8');
    await page.getByLabel('Maximum clip duration',{exact:true}).fill('12');
    await page.getByLabel('Selection mode',{exact:true}).selectOption('all');
    await page.getByLabel('Subtitle script',{exact:true}).selectOption('original');
    await page.getByText('Clip style & export settings',{exact:true}).click();
    await page.getByLabel('Generated quality',{exact:true}).selectOption('fast');
    const submitted=page.waitForResponse(r=>r.url().endsWith(base+'/highlights')&&r.request().method()==='POST');
    await page.getByRole('button',{name:'Generate 2 new clips',exact:true}).click();
    expect((await submitted).request().postDataJSON()).toMatchObject({clip_count:2,min_duration:8,max_duration:12});
    await expect.poll(async()=>{const v=await(await page.request.get(base)).json();return v.clips.length===2&&v.clips.every((c:{status:string})=>c.status==='ready');},{timeout:60000}).toBeTruthy();
    const saved=await(await page.request.get(base)).json();
    for(const c of saved.clips){
      expect(c.end-c.start).toBeGreaterThanOrEqual(8);expect(c.end-c.start).toBeLessThanOrEqual(12);
      const response=await page.request.get(base+'/media/'+c.id);expect(response.status()).toBe(200);
      fs.writeFileSync('artifacts/custom-duration-export.mp4',await response.body());
      const info=JSON.parse(execFileSync(python,['-c',"from backend import media; import json; print(json.dumps(media.probe('artifacts/custom-duration-export.mp4')))"],{encoding:'utf8'}));
      expect(info.duration).toBeGreaterThanOrEqual(7.9);expect(info.duration).toBeLessThanOrEqual(12.1);expect(info.has_audio).toBeTruthy();
    }
    await page.reload();await page.getByRole('button').filter({has:page.getByRole('heading',{name:p.name,exact:true})}).click();
    await page.locator('.ai-workflow-summary').click();
    await expect(page.getByLabel('Number of clips',{exact:true})).toHaveValue('2');
    await expect(page.getByLabel('Minimum clip duration',{exact:true})).toHaveValue('8');
    await expect(page.getByLabel('Maximum clip duration',{exact:true})).toHaveValue('12');
    await page.setViewportSize({width:390,height:844});
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBeTruthy();
    await page.screenshot({path:'artifacts/custom-duration-mobile.png',fullPage:true,animations:'disabled'});
  }finally{await page.request.delete(base).catch(()=>{});}
});
