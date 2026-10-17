import { defineConfig, devices } from '@playwright/test';
export default defineConfig({
 testDir:'./tests/browser', fullyParallel:true, forbidOnly:!!process.env.CI, retries:process.env.CI?1:0, workers:process.env.CI?2:undefined,
 reporter:[['list'],['html',{open:'never'}]],
 use:{baseURL:'http://127.0.0.1:3100',trace:'retain-on-failure',screenshot:'only-on-failure'},
 projects:[
  {name:'desktop',use:{...devices['Desktop Chrome'],colorScheme:'light',launchOptions:process.env.CHROMIUM_EXECUTABLE_PATH?{executablePath:process.env.CHROMIUM_EXECUTABLE_PATH,args:['--no-sandbox','--disable-dev-shm-usage']}:undefined}},
  {name:'dark',use:{...devices['Desktop Chrome'],colorScheme:'dark',launchOptions:process.env.CHROMIUM_EXECUTABLE_PATH?{executablePath:process.env.CHROMIUM_EXECUTABLE_PATH,args:['--no-sandbox','--disable-dev-shm-usage']}:undefined}},
  {name:'mobile',use:{...devices['Pixel 7'],launchOptions:process.env.CHROMIUM_EXECUTABLE_PATH?{executablePath:process.env.CHROMIUM_EXECUTABLE_PATH,args:['--no-sandbox','--disable-dev-shm-usage']}:undefined}},
  {name:'safari',use:{...devices['iPhone 13'],defaultBrowserType:'webkit'}}
 ],
 webServer:{command:'node tests/serve.mjs',url:'http://127.0.0.1:3100/readyz',reuseExistingServer:false,timeout:60000}
});
