# Backend

FastAPI, SQLite, FFmpeg/libass, faster-whisper and local translation/synthesis.
The existing Python package remains named `backend` to preserve API/module
compatibility. `run.py` sets up the import path and repository working directory,
so commands below work from this folder.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

On Linux/macOS, use `python3` and `.venv/bin/python`. API: http://127.0.0.1:8000;
OpenAPI docs: http://127.0.0.1:8000/docs. The default frontend is port 3000.

Copy `.env.example` to `.env` for custom settings; `run.py` loads this file.
Existing process environment variables take precedence. Private project data,
models and offline voice tools stay in `../data/`, preserving existing local
workspaces. Override with `CLIPFORGE_DATA` and `CLIPFORGE_TRANSLATION_MODELS` on
a persistent server. Keep a private backup. These files never belong in Git.

Render fonts are bundled in `../frontend/public/fonts`; clone the complete
repository when deploying the backend, even when only this service is started.

```powershell
.\.venv\Scripts\python.exe run.py setup-translation
.\.venv\Scripts\python.exe run.py setup-translation --pairs en:es
.\.venv\Scripts\python.exe run.py setup-dubbing
.\.venv\Scripts\python.exe run.py verify-whisper
.\.venv\Scripts\python.exe run.py test -q
```

Translation models and speech models download once. The voice setup installs
eSpeak NG locally on Windows; on Linux install `espeak-ng` with the package
manager. No paid translation/TTS key is needed. Not all recognition languages
have installed translation routes. Dubbing uses a basic synthetic voice and
does not animate mouths. Review output and consult the root README for limits.

To select the listening address/port:

```sh
python run.py --host 0.0.0.0 --port 8000
```

Run one backend process/replica. Jobs use in-process worker pools and persistent
local storage; they are not Vercel Functions or a distributed queue. For the
direct ASGI command from the repository root, use
`python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --workers 1`.
See [deployment](../docs/DEPLOYMENT.md) for trusted frontend origins and HTTPS.
