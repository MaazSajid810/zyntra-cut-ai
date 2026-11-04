# GitHub and Vercel deployment

The Git repository contains the application's source, configuration, tests and
bundled licensed fonts. Local projects, videos, databases, model caches, guest
sessions, restore keys, environment files and test artifacts remain on the
original computer and are excluded from Git. Publishing source does not migrate
the private workspace. Keep a separate private backup of `data/`.

## Hosting layout

| Component | Host and requirements |
| --- | --- |
| Next.js frontend | Vercel, Node.js 22, `npm ci`, `npm run build` |
| FastAPI + FFmpeg + speech/translation models | A continuously running Python host with CPU/RAM, HTTPS and a persistent writable disk |
| SQLite, source video, exports and model files | Persistent backend disk selected with `CLIPFORGE_DATA`; back up privately |

This backend uses in-process worker pools, not a durable distributed queue.
Vercel frontend/serverless functions cannot provide the current worker lifecycle
and persistent local storage. A frontend deployment without its live backend
cannot import, transcribe or render. The configuration fails the hosted build
when the backend origin is missing or points to localhost; it does not publish a
misleading local-only API destination.

## Configure the persistent backend first

Use Python 3.11 or 3.12 and install dependencies in a virtual environment:

```sh
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Set these variables in that host's service environment, substituting real paths
and the exact frontend URL (origins have no trailing slash):

```dotenv
CLIPFORGE_DATA=/var/lib/zyntracut
CLIPFORGE_TRANSLATION_MODELS=/var/lib/zyntracut/translations
CLIPFORGE_ALLOWED_ORIGINS=https://your-app.vercel.app,https://your-domain.example
CLIPFORGE_COOKIE_SECURE=true
CLIPFORGE_RENDER_WORKERS=1
CLIPFORGE_FAST_BATCH_SIZE=1
```

Create the data directory for the service user. Uvicorn does not automatically
load Next.js `.env.local`; configure variables explicitly on the backend host.
Install the optional translation packages once with the environment above:

```sh
.venv/bin/python -m scripts.setup_translation
```

For offline translated voices, install `espeak-ng` on the Python host (for
example with its operating-system package manager), or configure
`ESPEAK_NG_BINARY`. Install only the translation language pairs you need;
voice availability and installed translation routes are reported separately.
No cloud TTS credentials are used.

Start **one process/replica** behind the host's HTTPS reverse proxy:

```sh
.venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1
```

Do not enable auto-reload or multiple workers against the same SQLite/media
directory. Startup recovery marks interrupted processing as retryable errors;
it does not resume or redistribute jobs. A restart during rendering requires a
retry. Speech models download on first use into `CLIPFORGE_DATA/models`; retain
that disk and allow enough RAM/time for initialization. FFmpeg must support the
actual caption fonts/libass and chosen codecs. The local installation uses
`imageio-ffmpeg`; validate its build or set `FFMPEG_BINARY` on the host.

## Import the GitHub repository into Vercel

1. Connect the repository in Vercel's **Add New → Project** flow. If private,
   authorize the Vercel GitHub integration for this repository.
2. Select **Next.js**, repository root, Node.js **22.x**, install `npm ci` and
   build `npm run build`. `vercel.json` records framework/install/build defaults.
3. Add the server-only build variable:
   `CLIPFORGE_API_ORIGIN=https://your-real-backend.example.com`.
   Use the origin only; omit `/api`, credentials, query strings and fragments.
   Do not use a `NEXT_PUBLIC_` variable or include a token in the URL.
4. Add the actual Vercel/custom frontend origin to
   `CLIPFORGE_ALLOWED_ORIGINS` on the backend. Preview deployment URLs need their
   own explicit allowlist entry; do not permit every `*.vercel.app` origin.
5. Deploy/redeploy. The `/api/:path*` Next.js rewrite forwards to that backend's
   `/api/:path*`; changing the build variable requires a new deployment.

The default local backend remains `http://127.0.0.1:8000`; no local environment
change is necessary. Vercel account access and a reachable persistent backend
are required external inputs, and are not supplied by the source repository.

## Session, privacy and proxy checks

Keep browser API requests on the **frontend origin** through `/api`. The guest
cookie is HttpOnly, SameSite=Strict and host-only. The external rewrite and any
backend proxy must preserve `Cookie`, `Set-Cookie`, `Origin`, range headers and
`Cache-Control: private, no-store`. Do not enable shared caching on API/media
responses. Keep `CLIPFORGE_COOKIE_SECURE=true` behind HTTPS, even if the internal
proxy connects to Uvicorn over HTTP. A request origin is allowed explicitly;
the backend still rejects cross-site API requests. Do not weaken this to make
cross-origin browser calls to the backend directly.

After deployment, verify in **two fresh browser profiles**: bootstrap sessions,
upload/import a small video, inspect actual progress, generate clips, play a
rendered result, download it, edit and re-render, then delete. The other browser
must not see or fetch the first browser's projects/media. Reload and restart
checks should retain owned records and show honest interrupted-job errors.

Vercel's external-origin proxy has a 120-second idle response limit. Generation
requests enqueue background work and polling is used, but slow metadata/file
transfer requests can still hit host/proxy limits. The local Next.js 2 GiB body
and 30-minute proxy settings do **not** grant those limits on Vercel. Vercel
Functions also have separate payload limits; those are not a guarantee of what
an external rewrite accepts. Test the deployed upload and range-download path
before advertising large file support. Resumable uploads/direct object storage,
distributed jobs, account recovery, public-use quotas/rate limiting and billing
are additional production work; this preparation does not implement them.

Official references: [external rewrites](https://vercel.com/docs/routing/rewrites),
[proxy timeout](https://vercel.com/docs/limits#proxied-request-timeout),
[function limits](https://vercel.com/docs/functions/limitations).

## Commercial use and future advertising

No ad integration is enabled. Google Search Console is a separate search/site
verification service; AdSense is the advertising product. Any later ads require
an approved site/account, the owner's publisher ID and an appropriate placement.
An isolated loading/progress screen is not an appropriate default ad placement:
Google prohibits ads on screens without publisher content or used for alerts,
navigation or behavioral purposes. Keep processing progress functional and do
not delay rendering to create ad impressions. See
[Google Publisher Policies](https://support.google.com/adsense/answer/10502938?hl=en).

Vercel Hobby is for personal, non-commercial use; advertisements including
AdSense count as commercial use under its guidelines. A later ad-funded release
needs a suitable hosting plan. See [Vercel fair use](https://vercel.com/docs/limits/fair-use-guidelines).

## Configuration verification

```sh
node --test tests/deployment-config.test.mjs
npm run typecheck
npm run build
```

These checks validate configuration and the local frontend. They do not prove
that a new hosting provider supports your processing workload. Only a live
end-to-end test on the configured frontend and backend can establish that.
