import {defineConfig} from '@playwright/test';
import path from 'node:path';
const frontend=__dirname;
const junit=process.env.PLAYWRIGHT_JUNIT_OUTPUT_FILE;
if(junit&&!path.isAbsolute(junit))process.env.PLAYWRIGHT_JUNIT_OUTPUT_FILE=path.resolve(junit);
process.chdir(path.resolve(frontend,'..'));
export default defineConfig({testDir:path.join(frontend,'tests/browser'),outputDir:path.resolve('test-results'),use:{baseURL:'http://127.0.0.1:3000',headless:true,channel:process.env.CLIPFORGE_BROWSER_CHANNEL,trace:'retain-on-failure',screenshot:'only-on-failure'},timeout:180000,workers:1});
