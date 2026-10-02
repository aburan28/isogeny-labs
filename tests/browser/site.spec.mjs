import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { readdirSync } from 'node:fs';
const pages=['/index.html',...['notes','schemes','cryptanalysis','contact'].flatMap(folder=>readdirSync(`_site/${folder}`).filter(p=>p.endsWith('.html')).map(p=>`/${folder}/${p}`))];
test.beforeEach(async ({page})=>{await page.route(/https:\/\/fonts\.(googleapis|gstatic)\.com\//,route=>route.fulfill({status:200,body:''}));});
for(const path of pages) test(`page health ${path}`,async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const response=await page.goto(path);expect(response.status()).toBe(200);
 await expect(page.getByRole('main')).toBeVisible();await expect(page.locator('h1')).toHaveCount(1);
 await expect(page.getByRole('navigation',{name:'Main',exact:true})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
 expect(errors).toEqual([]);
});
test('trait explorer filters, searches, clears and expands deep links',async({page})=>{
 await page.goto('/notes/curve-traits.html');await expect(page.locator('.trait')).toHaveCount(30);
 await page.getByLabel('Source',{exact:true}).selectOption('dissect');await expect(page.locator('.trait:visible')).toHaveCount(22);
 await page.getByLabel('Source',{exact:true}).selectOption('foundation');await expect(page.locator('.trait:visible')).toHaveCount(8);
 await page.getByLabel('Search traits').fill('no-such-trait');await expect(page.locator('#no-results')).toBeVisible();
 await page.getByRole('button',{name:'Clear filters'}).click();await expect(page.locator('.trait:visible')).toHaveCount(30);
 await page.goto('/notes/curve-traits.html#trait-10');await expect(page.locator('#trait-10')).toHaveAttribute('open','');
 await page.locator('#trait-10 summary').focus();await page.keyboard.press('Enter');await expect(page.locator('#trait-10')).not.toHaveAttribute('open','');
});
test('home and Notes index expose the traits guide',async({page})=>{
 await page.goto('/index.html');await page.getByRole('link',{name:'Elliptic curve traits and their security connections',exact:true}).click();await expect(page).toHaveURL(/curve-traits.html$/);
 await page.goto('/notes/index.html');await expect(page.locator('a[href="curve-traits.html"]')).toBeVisible();
});
test('learning content works without JavaScript',async({browser})=>{
 const context=await browser.newContext({javaScriptEnabled:false});const page=await context.newPage();await page.goto('http://127.0.0.1:3100/notes/curve-traits.html');await expect(page.locator('.trait')).toHaveCount(30);await expect(page.locator('#filters')).toBeHidden();await context.close();
});
for(const path of ['/index.html','/notes/curve-traits.html','/contact/index.html'])test(`accessibility ${path}`,async({page})=>{
 await page.goto(path); if(path.includes('contact'))await expect(page.getByLabel('Work email')).toBeVisible();
 const result=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();expect(result.violations).toEqual([]);
 await page.screenshot({path:test.info().outputPath('page.png'),fullPage:true});
});
