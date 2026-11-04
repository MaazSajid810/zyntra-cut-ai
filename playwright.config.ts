import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./tests/browser',use:{baseURL:'http://127.0.0.1:3000',headless:true,channel:process.env.CLIPFORGE_BROWSER_CHANNEL,trace:'retain-on-failure',screenshot:'only-on-failure'},timeout:180000,workers:1});
