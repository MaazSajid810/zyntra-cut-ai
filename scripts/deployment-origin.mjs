/** Resolve the build-time, server-only destination for the same-origin API. */
export function apiOrigin(env = process.env) {
  const hosted = Boolean(env.VERCEL);
  const raw = env.CLIPFORGE_API_ORIGIN?.trim();
  if (hosted && !raw) {
    throw new Error('Set CLIPFORGE_API_ORIGIN to your persistent HTTPS backend before deploying to Vercel. Local Python/FFmpeg processing cannot run in the frontend deployment.');
  }
  let origin;
  try { origin = new URL(raw || 'http://127.0.0.1:8000'); }
  catch { throw new Error('CLIPFORGE_API_ORIGIN must be an absolute HTTP(S) origin.'); }
  if (!['http:', 'https:'].includes(origin.protocol) || origin.username || origin.password ||
      origin.pathname !== '/' || origin.search || origin.hash) {
    throw new Error('CLIPFORGE_API_ORIGIN must contain only an HTTP(S) origin, without credentials, a path, query or fragment.');
  }
  const host = origin.hostname.replace(/^\[|\]$/g, '').replace(/\.$/, '').toLowerCase();
  const parts = host.split('.').map(Number);
  const privateV4 = /^\d+\.\d+\.\d+\.\d+$/.test(host) && (
    [0, 10, 127].includes(parts[0]) || parts[0] >= 224 ||
    (parts[0] === 169 && parts[1] === 254) ||
    (parts[0] === 172 && parts[1] >= 16 && parts[1] <= 31) ||
    (parts[0] === 192 && parts[1] === 168) ||
    (parts[0] === 100 && parts[1] >= 64 && parts[1] <= 127)
  );
  const privateHost = host === 'localhost' || host.endsWith('.localhost') || host.endsWith('.local') ||
    privateV4 || host === '::' || host === '::1' ||
    (host.includes(':') && /^(?:fc|fd|fe[89ab]|::ffff:)/.test(host));
  if (hosted && (origin.protocol !== 'https:' || privateHost || (!host.includes('.') && !host.includes(':')))) {
    throw new Error('A Vercel deployment requires CLIPFORGE_API_ORIGIN to be a public HTTPS backend, not localhost or a private network address.');
  }
  return origin.origin;
}
