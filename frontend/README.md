# Frontend

Next.js / React / TypeScript interface for ZyntraCut AI. Run commands in this folder:

```sh
npm ci
npm run dev
```

Open http://127.0.0.1:3000. The Python service must be running on port 8000.
The frontend proxies `/api/*` to that service; no backend code is bundled into
the browser. Relative imports and bundled `/fonts/*` assets stay inside this folder.

For a remote backend, copy `.env.example` to `.env.local`, configure
`CLIPFORGE_API_ORIGIN`, then rebuild. Backend requests need a trusted configured
frontend origin. Never put private API keys into `NEXT_PUBLIC_*` variables.

```sh
npm run typecheck
npm run test:config
npm run build
npm run start
```

Do not rebuild the directory currently served by a production Next.js process.
For a parallel update, set `ZYNTRACUT_BUILD_DIR` to a fresh `.next-...` directory
and start the verified release with the same setting.

For browser tests, keep both services running and use `npm run test:e2e`.
Playwright stores fixtures/artifacts at the repository root and resolves the
Python executable from `backend/.venv`, a legacy root `.venv`, or the explicit
`CLIPFORGE_TEST_PYTHON` environment variable. Tests needing real speech use the
public sample downloaded by `python run.py verify-whisper` in `backend/`.

Vercel **Root Directory** must be `frontend`; see [deployment](../docs/DEPLOYMENT.md).
