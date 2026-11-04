import {test,expect} from '@playwright/test';

test('studio theme, sidebar and responsive settings remain functional',async({page})=>{
  await page.goto('/workspace');
  await expect(page).toHaveTitle(/ZyntraCut AI/);
  await expect(page.locator('.brand')).toContainText('ZyntraCut');
  await page.setViewportSize({width:1440,height:1000});
  await page.getByRole('button',{name:'Collapse sidebar',exact:true}).click();
  await expect(page.locator('.shell')).toHaveClass(/compact/);
  await page.getByRole('button',{name:'Expand sidebar',exact:true}).click();
  await expect(page.locator('.shell')).not.toHaveClass(/compact/);
  await page.getByRole('button',{name:'Link to clips',exact:true}).click();
  const studio=page.getByRole('region',{name:'Public link to clips'});
  await studio.locator('.import-customization>summary').click();
  await expect(studio.getByRole('heading',{name:'Clip settings',exact:true})).toBeVisible();
  await studio.getByRole('button',{name:'Gaming',exact:false}).click();
  await expect(studio.getByRole('combobox',{name:'Caption design',exact:true})).toHaveValue('yellow');
  await expect(studio.getByLabel('Caption font',{exact:true})).toHaveValue('Bangers');
  await expect(studio.getByLabel('Import aspect ratio',{exact:true})).toHaveValue('vertical');
  await studio.getByLabel('Clip count slider',{exact:true}).fill('12');
  await expect(studio.getByLabel('Clips to generate',{exact:true})).toHaveValue('12');
  await studio.getByLabel('Engagement score slider',{exact:true}).fill('80');
  await expect(studio.getByLabel('Import minimum engagement score',{exact:true})).toHaveValue('80');
  await studio.getByRole('button',{name:'TikTok',exact:false}).click();
  await expect(studio.getByLabel('Public video link')).toBeFocused();
  await expect(studio.getByLabel('Public video link')).toHaveAttribute('placeholder',/TikTok/);
  const chooser=page.waitForEvent('filechooser');
  await studio.getByRole('button',{name:'Upload file',exact:true}).click();
  await (await chooser).setFiles([]);
  for(const width of [1440,1024,768,390]){
    await page.setViewportSize({width,height:1000});
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
    await expect(studio.getByLabel('Public video link')).toBeVisible();
    await expect(studio.getByRole('button',{name:'Get clips',exact:true})).toBeVisible();
    if(width===1440||width===390){
      await page.evaluate(()=>window.scrollTo(0,0));
      await page.screenshot({animations:'disabled',path:`artifacts/reference-ui-${width}.png`,fullPage:true});
    }
  }
  await page.emulateMedia({reducedMotion:'reduce'});
  expect(await page.locator('.studio-hero').evaluate(el=>getComputedStyle(el).animationName)).toBe('none');
});
