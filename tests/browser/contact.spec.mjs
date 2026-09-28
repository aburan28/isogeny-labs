import {test,expect} from '@playwright/test';
async function fill(page){await page.getByLabel('Your name').fill('Example Person');await page.getByLabel('Work email').fill('contact@example.invalid');await page.getByLabel('Organization',{exact:true}).fill('Example Enterprise');await page.getByLabel('What can we help with?').selectOption('Security review');await page.getByLabel('Project overview').fill('We need an initial review of our planned cryptographic integration.');await page.getByRole('checkbox').check();}
test('valid inquiry is acknowledged by the real API',async({page})=>{
 await page.goto('/contact/index.html');await fill(page);await page.getByRole('button',{name:'Send inquiry'}).click();await expect(page.getByRole('heading',{name:'Inquiry received'})).toBeVisible();await expect(page.getByRole('status')).toContainText('contact@example.invalid');
});
test('required fields and consent prevent submission',async({page})=>{
 let requests=0;page.on('request',r=>{if(r.url().endsWith('/api/inquiries'))requests++});await page.goto('/contact/index.html');await page.getByRole('button',{name:'Send inquiry'}).click();await expect(page.getByLabel('Your name')).toBeFocused();expect(requests).toBe(0);
 await fill(page);await page.getByRole('checkbox').uncheck();await page.getByRole('button',{name:'Send inquiry'}).click();await expect(page.getByRole('checkbox')).toBeFocused();expect(requests).toBe(0);
});
test('storage failure retains input and retry identifier',async({page})=>{
 const keys=[];await page.route('**/api/inquiries',async route=>{keys.push(route.request().headers()['idempotency-key']);await route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:'We could not save your inquiry. Please retry shortly.'})})});
 await page.goto('/contact/index.html');await fill(page);await page.getByRole('button',{name:'Send inquiry'}).click();await expect(page.getByRole('alert')).toContainText('could not save');await expect(page.getByLabel('Work email')).toHaveValue('contact@example.invalid');await page.getByRole('button',{name:'Send inquiry'}).click();await expect.poll(()=>keys.length).toBe(2);expect(keys[0]).toBe(keys[1]);await expect(page.getByRole('heading',{name:'Inquiry received'})).toHaveCount(0);
});
test('shows rate limit and network failures without false success',async({page})=>{
 await page.route('**/api/inquiries',route=>route.fulfill({status:429,contentType:'application/json',body:'{}'}));await page.goto('/contact/index.html');await fill(page);await page.getByRole('button',{name:'Send inquiry'}).click();await expect(page.getByRole('alert')).toContainText('10 minutes');
 await page.unroute('**/api/inquiries');await page.route('**/api/inquiries',route=>route.abort());await page.getByRole('button',{name:'Send inquiry'}).click();await expect(page.getByRole('alert')).toContainText('could not reach');
});
test('pending request disables repeat submit',async({page})=>{
 let finish;await page.route('**/api/inquiries',async route=>{await new Promise(resolve=>{finish=resolve});await route.fulfill({status:503,contentType:'application/json',body:'{"error":"Try later"}'})});await page.goto('/contact/index.html');await fill(page);await page.getByRole('button',{name:'Send inquiry'}).click();await expect(page.getByRole('button',{name:'Sending…'})).toBeDisabled();finish();await expect(page.getByRole('alert')).toBeVisible();
});
