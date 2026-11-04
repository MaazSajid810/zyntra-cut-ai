import type { NextConfig } from 'next';
import { apiOrigin } from './scripts/deployment-origin.mjs';
const backendOrigin = apiOrigin();
const config: NextConfig = {
  // Build a new release separately while the current frontend keeps serving.
  // Start that release with the same directory setting; never rebuild its active output.
  distDir: process.env.ZYNTRACUT_BUILD_DIR || '.next',
  experimental: {
    // Include multipart headers above the API's 2 GiB file limit.
    proxyClientMaxBodySize: 2 * 1024 ** 3 + 1024 ** 2,
    proxyTimeout: 30 * 60 * 1000,
  },
  async rewrites() { return [{ source: '/api/:path*', destination: `${backendOrigin}/api/:path*` }]; },
};
export default config;
