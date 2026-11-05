# GitHub and deployment

The source repository has separate frontend/ and backend/ folders. Publishing
source does not migrate private videos, databases, sessions or model caches.

## Frontend on Vercel

1. Import MaazSajid810/zyntra-cut-ai into Vercel.
2. Set **Root Directory = frontend** and framework **Next.js**.
3. Select Node.js 22.x, install command `npm ci`, build command `npm run build`.
4. Configure `CLIPFORGE_API_ORIGIN=https://your-real-backend.example.com`.
5. Add the exact frontend origin to backend `CLIPFORGE_ALLOWED_ORIGINS`.

The backend origin is compiled at build time; rebuild after changing it.
Hosted builds reject a missing, localhost or private-network backend origin.
The root-directory setting is essential: package.json and vercel.json are inside
frontend/. Vercel does not run the persistent Python video-processing workers.

## Persistent Python backend

Clone the complete repository, including frontend/public/fonts. Use Python
3.11-3.13 and run these commands from backend/:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Copy backend/.env.example to backend/.env, or configure the service environment:

```dotenv
CLIPFORGE_DATA=/var/lib/zyntracut
CLIPFORGE_TRANSLATION_MODELS=/var/lib/zyntracut/translations
CLIPFORGE_ALLOWED_ORIGINS=https://your-app.vercel.app,https://your-domain.example
CLIPFORGE_COOKIE_SECURE=true
CLIPFORGE_RENDER_WORKERS=1
CLIPFORGE_FAST_BATCH_SIZE=1
```

Create persistent directories owned by the service user. Install optional
translation models and the operating-system espeak-ng package for offline voices:

```sh
.venv/bin/python run.py setup-translation
.venv/bin/python run.py --host 0.0.0.0 --port 8000
```

Run **one process/replica** behind an HTTPS reverse proxy. Use persistent storage
for SQLite, source video, exports and models, with private backups. Startup
recovery marks interrupted jobs for retry; this is not a distributed queue.
The local default remains the repository-root data/ folder for compatibility.

Configure sufficient upload limits, timeouts, CPU, RAM and disk. The API allows
up to 2 GB / 4 hours, but the chosen host can impose lower limits. Verify
FFmpeg/libass, fonts and chosen codecs on the actual server.

## Verify a deployment

Check frontend /api/health, a real small upload, captions, rendering, playback
and a manual download. Verify that two isolated browser sessions cannot access
each other's projects. Keep secure cookies, exact allowed origins and ownership
checks. Do not serve private data directories publicly.

Uploading these source folders to GitHub does not create a public processing
host or Vercel deployment. The local setup works without paid API credentials.
