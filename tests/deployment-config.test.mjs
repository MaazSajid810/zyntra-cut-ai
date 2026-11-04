import test from 'node:test';
import assert from 'node:assert/strict';
import { apiOrigin } from '../scripts/deployment-origin.mjs';

test('local default and explicit external origin preserve the API path contract', () => {
  assert.equal(apiOrigin({}), 'http://127.0.0.1:8000');
  assert.equal(apiOrigin({ CLIPFORGE_API_ORIGIN: ' https://backend.example.com/ ' }), 'https://backend.example.com');
});

test('Vercel cannot silently deploy a localhost or missing processing backend', () => {
  for (const origin of ['', 'http://backend.example.com', 'https://localhost:8000',
    'https://127.0.0.1', 'https://10.1.1.1', 'https://192.168.1.2',
    'https://172.16.4.2', 'https://[::1]', 'https://api.localhost', 'https://api.local']) {
    assert.throws(() => apiOrigin({ VERCEL: '1', CLIPFORGE_API_ORIGIN: origin }), /CLIPFORGE_API_ORIGIN/);
  }
  assert.equal(apiOrigin({ VERCEL: '1', CLIPFORGE_API_ORIGIN: 'https://api.example.com' }), 'https://api.example.com');
  assert.equal(apiOrigin({ VERCEL: '1', CLIPFORGE_API_ORIGIN: 'https://fcdn.example.com' }), 'https://fcdn.example.com');
});

test('reject credentials, paths and query strings instead of leaking or misrouting them', () => {
  for (const origin of ['not-a-url', 'ftp://api.example.com', 'https://user:password@api.example.com',
    'https://api.example.com/api', 'https://api.example.com/?token=secret', 'https://api.example.com/#fragment']) {
    assert.throws(() => apiOrigin({ CLIPFORGE_API_ORIGIN: origin }), /CLIPFORGE_API_ORIGIN/);
  }
});
