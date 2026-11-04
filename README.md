# ZyntraCut AI

An original local video clipping studio built with Next.js, TypeScript, Tailwind/CSS, FastAPI, SQLite, FFmpeg/libass and faster-whisper. Public name: **ZyntraCut AI**. Existing ClipForge folders, API paths and guest-session keys remain compatible with saved projects.

The independent creator platform follows the latest dark/green clipping reference: **Create, Explore, Wizard and Studio**. Source settings, processing, clip previews and editing stay on Create; the standalone full editor remains available. References inform original layouts; no competitor service, brand or creator media is integrated. See [PLATFORM_UPGRADE.md](PLATFORM_UPGRADE.md), [VALIDATION.md](VALIDATION.md) and [STUDIO_REFERENCE.md](STUDIO_REFERENCE.md) for working features and limits.


## Screenshots

These are captures of the running local app in an isolated guest workspace.
The sample title video was rendered by Studio; no private user media is shown.

| Create | Clip review |
| --- | --- |
| ![Create clips](docs/screenshots/create.png) | ![Rendered clip review](docs/screenshots/clips.png) |

| Visual editor | Local Studio |
| --- | --- |
| ![Caption and video editor](docs/screenshots/editor.png) | ![Local title and photo studio](docs/screenshots/studio.png) |

[Wizard workspace](docs/screenshots/wizard.png)

## Ratio, shared edits and native languages

The simple Create settings now expose **Original, 9:16, 1:1, 16:9 and 4:5** beside
caption language and clip length. The existing Original default is retained.
In the selected clip editor, **Apply edits to all clips** is visible above the
visual editor. Copy current styling to drafts, or apply and re-render every clip.
Ratio, captions styling, effects, audio, branding and layer settings are shared;
each clip retains its own title and source start/end. Spoken caption text remains
project-wide. Layer timing must fit every target clip; incompatible edits are
rejected before changing the project.

Spoken-language choices include Punjabi, Pashto, Sindhi, Spanish and the other
Whisper language tokens. Caption outputs include Original, Roman Urdu, Urdu,
Hindi, English, Punjabi, Pashto, Sindhi, Spanish, French, Arabic, Bengali, German,
Portuguese and Italian. This list does **not** mean every translation model is
installed. Original and same-language native captions preserve recognized words
and timestamps. `/api/languages` reports installed translation routes; the UI
labels native-only outputs and explains incompatible choices. Unsupported
translation keeps Original captions and a notice rather than inventing text.
Models and dialects vary in accuracy; review native recognition and translated
meaning. Caption options change subtitles; the separate Transcript dubbing panel can replace audio with a timed offline synthetic voice.
Cantonese requires a speech model with that language token; older models can
reject it with an actionable message.

English-to-Spanish translation was installed and tested locally. Additional
Argos model packages can be explicitly installed with
`python -m scripts.setup_translation --languages es` (or another configured code).
Available languages and installed direction pairs are different. Downloads or
unsupported package formats can fail without losing existing models or projects.
New Gurmukhi and Bengali fonts complement existing Arabic/Devanagari fonts for
native-script caption rendering. Model caches and private videos are excluded
from Git publication.


## Caption repair, offline dubbing and batch exports

In **Transcript**, choose the actual **Spoken language**, independently of the
subtitle output. **Detect & repair captions** reruns accurate recognition with
automatic language detection and keeps up to three previous transcript snapshots
in the private project record. Existing clip ranges remain intact; old MP4 files
are kept on disk while new exports become drafts. Recognition samples up to three language windows and resets text context between
windows to avoid carrying an intro hallucination through a long video. Repeated
or unreadable token loops are rejected with a repair message. A confident disagreement
between forced source language and independently detected speech is shown as a
warning; an explicit source language is never silently changed.

Install the optional lightweight offline voice engine once:

```powershell
.\.venv\Scripts\python.exe -m scripts.setup_dubbing
```

Linux servers can install `espeak-ng` with their package manager. A custom binary
can be selected with `ESPEAK_NG_BINARY`. The Windows setup extracts a versioned,
checksum-verified official eSpeak NG package into ignored `data/tools`; it does
not require a cloud key. eSpeak NG is GPL licensed; see its
[upstream license and source](https://github.com/espeak-ng/espeak-ng).

Then open **Transcript ? Translate captions + voice**, choose an available
language and click the button. Only languages with both an installed translation
route and offline voice are enabled. Local English/Urdu/Hindi and English-to-Spanish
models were tested; this is not universal translation. Voices are basic synthetic
speech, without voice cloning. Each sentence fits its original timeline slot;
overlong translations fail with a correction message rather than cutting words.
The dubbed track replaces all source audio, including background music; add your
own music in the editor if needed. Existing clips can render automatically with
the new voice. **Use original audio** restores source audio for new exports.
Editing dubbed caption wording/timing requires regenerating the voice before export.

**Mouth animation is not implemented.** Dubbing does not reshape a person's lips.
The inspected laptop has Intel HD Graphics 520 and about 8 GB system RAM. Heavy
neural lip-sync models require a compatible GPU and additional models; no
unverified lip-sync result or toggle is presented.

Saved-transcript generation runs as a background job from the UI, so the page
can keep polling while source analysis/translation finishes. A request for ten
clips is a maximum: duration, score, overlap and duplicate rules still apply.
Errors are saved on the project and shown on the same page. Explore thumbnails
use a fixed YouTube-ID image endpoint instead of cached signed image links;
unavailable images have a readable fallback and never block importing.

## Creator platform

- **Create** (`/` or `/dashboard`): real source metadata, upload/import, custom count and duration, progress, same-page clip previews/editor, sorting, confirmed individual/selected deletion and private recent projects.
- **Explore** (`/explore`): category-based public YouTube discovery and private source library. This is relevance search, not a verified trending chart; growth needs repeated observations.
- **Wizard** (`/wizard`): supported local commands with review before execution, private saved history, real clip editing/rendering and manual downloads. Examples: `generate 5 clips, 15-30 seconds`, `captions yellow`, `font size 72`, `trim 2-15`, `vertical`, `speed 1.2x`, `voice deep`, `render`. It is not a general conversational AI model.
- **Studio** (`/studio`): create actual PNG title designs or animated portrait text/photo MP4s, entirely locally. Select style/size/duration, optionally upload a photo, preview, download or open the video in the full editor. This does not synthesize photorealistic footage from a scene prompt; no heavy generative model was installed.
- **Full editor** (`/editor?project=...&clip=...`) and **original workspace** (`/workspace`) preserve captions, timeline, effects, audio, branding, layers, exports and guest ownership.

**Roman Urdu:** Create par video/link dein aur clips ki tadaad/duration chunen. Explore se source chun sakte hain. Wizard mein diye gaye commands pehle review karein, phir Run this action dabayen. Studio aapke words/photo se design ya motion video banata hai; naya photorealistic scene generate nahi karta. Preview ke baad Download aap khud karte hain. Koi login ya paid credits zaroori nahi.

## Run on Windows

Use Python 3.11–3.13 and Node.js 22.19 or newer. In `ClipForge_Ready`, install dependencies when needed:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm install
# One-time local English/Urdu/Hindi translation models:
.\.venv\Scripts\python.exe -m scripts.setup_translation
```

Start the backend and frontend in two terminals:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

```powershell
node node_modules/next/dist/bin/next dev --hostname 127.0.0.1
```

Open **http://127.0.0.1:3000** in Microsoft Edge. For a production build, stop the frontend, run `npm run build`, then `npm run start`. Do not replace build files while a production frontend is serving them. Backend API documentation: http://127.0.0.1:8000/docs.

To prepare an update while the current frontend remains available, set
`ZYNTRACUT_BUILD_DIR` to a fresh `.next-...` directory before building. Preview
and start that release with the same setting; never build over the active
release's directory. The selected directory can be saved in the ignored
`.env.local` file so subsequent starts use the verified release. Alternate
preview ports remain subject to the backend's existing origin checks.

If the browser connection is interrupted, the import form shows a connection
message rather than raw `Failed to fetch`. Project/status polling clears its
temporary error after a successful response. Accepted import jobs keep their
ID and resume polling; failed POST requests are not replayed automatically.
Check Library before explicitly submitting a video again when its acceptance
is uncertain. Refresh after an app update to load the latest interface.

If the machine's global npm wrapper is broken, the existing local npm copy can be invoked with `node package/bin/npm-cli.js install --cache .npm-cache`. `package-lock.json` and `requirements.lock.txt` record installed dependencies. FFmpeg comes from imageio-ffmpeg; no separate system installation is needed.

## Generate, review, edit and download

1. Upload a real video, or paste a supported public video URL. File uploads support known-duration videos up to 2 GB/four hours; maximum-size processing has not been stress tested.
2. Choose **Auto quantity** for qualified, distinct moments up to 100, or select any whole clip count from **1 to 100** using the custom field or 5/10/30/100 shortcuts. The count is a maximum: insufficient speech, existing ranges and quality thresholds can produce fewer or zero new clips. Existing clips are preserved. Quality first uses source-speech hooks/payoffs, cached audio levels/silence and sampled visual changes. These are explainable heuristics, not probabilities of views. Short sources adapt the minimum duration rather than creating duplicate clips. Explore all is an explicit lower-scoring alternative.
3. Set **Spoken language** independently from **Subtitle language / script**. Choose Original, Urdu, Hindi, Roman Urdu or English output. Pick the actual Urdu/Hindi/English source language if automatic detection is wrong.
4. Generate. Real download, transcription and rendering states appear in the processing card. The first generation transcribes the full source; later requests reuse saved text where compatible. Automatic preview preparation is enabled by default. It never starts a browser download.
5. Select a clip and watch its rendered preview. Save and render after changing settings. **Apply & render** updates the actual video; selecting a filter alone does not change an existing export.
6. Download only the clips you want. MP4 uses H.264/AAC with fast-start metadata; WebM uses VP9/Opus. Saved subtitles also download as SRT or VTT.

**Roman Urdu:** Video upload karein ya public link paste karein. Clips ki tadaad aur boli jane wali zubaan chunen; subtitles Urdu, Hindi, Roman Urdu ya English mein rakh sakte hain. Generate dabayen aur status ka intezar karein. Preview dekhein, zaroorat par Transcript mein words theek karein, phir Apply & render karein. Download sirf aapke click par hota hai.

## Source preview, recovery and quantity

Paste a link and click **Get clips** to read its actual title, thumbnail and duration. This metadata step does not download a video or create a project. Choose language, duration and any custom count from 1–100, then click **Create AI Clips**. Processing and previews stay on Create. If metadata fails, **Import without preview** explicitly retries the regular import. A successful metadata preview does not guarantee download access.

**Roman Urdu:** Link paste kar ke Get clips dabayen. Pehle source ki details aayengi. Zubaan, clips ki tadaad aur duration chun kar Create AI Clips dabayen. Status, clips aur editor isi page par hain. Preview dekh kar sirf pasand ke clips download karein.

Captions default to **Original / No translation**. Unsupported local translation keeps original recognized words and timings, saves the requested choice and displays a notice. It does not invent a translation. **Recover saved speech & generate** reuses already saved speech after a failed import without downloading/transcribing again, preserving existing clips and strict generation settings.

Clip count is a requested maximum. A 41:30 source can contain at most 41 separate clips of at least 60 seconds, before quality rules and pauses. Scores are explainable heuristics, not probabilities of views. Lowering a score or choosing **Explore all suggestions** is an explicit user decision.

## Captions, translation and synchronization

Whisper produces actual word timestamps. Aligned native captions support word-by-word or karaoke highlighting, pop/bounce/scale/fade animation, fonts, size, colors, contrast and position. Manual changes that no longer match word alignment use readable phrase captions rather than invented word timestamps.

Roman Urdu transliterates Urdu/Hindi words. Different output languages use installed local Argos/OpenNMT translation models through CTranslate2 and SentencePiece. Supported translation languages are English, Urdu and Hindi; Roman output can follow Urdu translation. No transcript is sent to a translation API. Models install once with `scripts.setup_translation`; recorded sources/checksums and package documentation remain under `data/translations`. `CLIPFORGE_TRANSLATION_MODELS` can point to another installed-model directory.

Translation is **not word-perfect**. In actual testing, a negative statement lost its negation. The application shows original text beside translated captions and flags possible missing negation for review. This limited check does not prove that every unflagged translation is correct. Proper names, recognition and Roman spelling can also be wrong. Translated words cannot inherit reordered source-word timestamps; their phrase timing derives from the recognized source segment and may be approximate inside it.

**Transcript → Re-transcribe audio** replaces old incorrect recognition using the selected source/output language. It can replace manual edits; confirmation explains that clip ranges stay intact and exports become drafts. Changing script alone cannot fix words Whisper misheard. Original output restores the available native snapshot; manual transcript edits clear obsolete snapshots so later conversion does not silently overwrite edits.

Audio is normalized to the video timeline before recognition, preserving delayed starts and gaps. **Caption sync**, in Captions, adjusts an individual clip by -5 to +5 output seconds: positive delays captions, negative shows them earlier. It affects burned-in captions and clip-relative SRT/VTT consistently, including sped-up exports. Whole-project subtitles keep original source time. Re-render to inspect the result.

## Editing tools

- **Frame & trim:** source start/end, original/9:16/1:1/16:9/4:5 ratios, full-frame fit or fixed adjustable crop, and 1x–4x speed. Audio/captions follow output speed. Original ratio preserves small-source dimensions instead of inventing detail.
- **Captions:** fourteen caption styles including disabled subtitles, bundled font choices, active-word highlighting and seven caption/motion presets. **Neon glow** adds a pink halo; **Neon word highlight** lights the active timed word. Edited/translated captions without matching word timestamps use a readable glowing phrase. Both presets work in the importer, editor and shared edits. Urdu and Hindi use compatible bundled Noto fonts. Presets apply real caption/zoom/leveling settings; they do not add music or branding.
- **Effects:** original/vivid/warm/cool/mono/vintage/mirror plus cinematic/sepia/soft/sharpen/blur; gentle or stronger rhythmic zoom. Transitions currently provide black/white beginning/end fades and B-roll dissolve, not arbitrary multi-clip transition editing.
- **Audio:** deep/high pitch with strength, radio, echo or source mute; loudness leveling and steady-noise reduction. Upload background music, set volume, and schedule synthesized pop/ding/whoosh effects. Music loops and fades at the end. Source mute keeps separately added music/SFX. These are audio transformations, not voice cloning or a replacement speaker.
- **Branding:** opt in to channel text and/or upload a static PNG/JPEG/WebP logo. Adjust opacity/size/color, drag text/logo in the placement guide, use arrow keys (Shift for larger steps), or set X/Y sliders. Low-opacity branding is rendered into the exported clip. The guide uses a source frame; final filters/captions appear after rendering.
- **B-roll:** upload your own supporting video, choose full-frame or picture-in-picture, and set output start/end. Short footage loops; original speech continues and captions stay above it. One B-roll asset is supported per clip. No stock video is fetched automatically.
- **Photos:** in **B-roll & images**, upload a static PNG, JPEG or WebP photo (up to 20 MB / 4096 px). Choose a movable overlay or full-frame cutaway, set output start/end, opacity and width, then drag or use keyboard/X/Y controls for placement. Full-frame mode offers whole-image padding or fill-with-cropping. Source speech continues and captions render above the photo. A separate channel logo can remain enabled. Apply & render updates preview/export. These photos attach to an existing video project; a standalone image-to-video project flow is not implemented.
- **Stickers & text:** explicitly enable follow/subscribe/like badges; choose start/middle/end/custom timing and pop/fade/slide animation. Custom on-screen text is distinct from speech captions. No default FOLLOW badge, app watermark or unsolicited branding is added.
- **Source covers:** fixed black webcam and burned-caption bands can cover selected source content. They also hide anything behind that area; this is not text erasing, face tracking or background reconstruction. Separate subtitle tracks are excluded from exports.
- **Export:** 480p/720p/1080p and MP4/WebM, individual or batch rendering. Lower quality is quicker; source detail cannot be restored by choosing 1080p. Save/apply styles to drafts or explicitly re-render all selected existing clips.

The selected-clip workspace places the player beside contextual tool panels, with an editable timeline below. Drag or keyboard-trim the source range, move/trim photo and B-roll timing, seek captions, zoom the timeline and undo/redo edits. Source waveforms come from cached audio measurements. Save changes or Apply & render to commit; edited effects require rendering for a final preview. Arbitrary multiple video/audio sequences, split/merge/ripple edits, keyframes and a real-time compositor remain future work.

## Projects, privacy and deletion

Each browser guest receives a private session without login. Ownership checks protect project, clip, asset and import APIs; knowing another project's ID is insufficient. Different browser profiles have different workspaces. Clearing the guest cookie can lose access: this is not an account-based recovery service. Do not clear it to troubleshoot rendering.

**Delete project** removes the project and its media. Each clip has its own Delete action. In All clips/Exports, select checkboxes or **Select all visible clips**, then **Delete selected**. Search limits the selected set. A confirmation precedes deletion, and partial failures retain failed selections for retry. Deleting clips keeps the source and other clips. Busy projects are locked until jobs finish. Old export revisions remain on disk until their clip/project is deleted. On Windows, project deletion releases the preview and stages the directory before committing database deletion; a locked stage leaves the project intact with a retry message. Committed files still held by a response are cleaned up privately with retries. Startup restores an uncommitted staged project after a crash.

SQLite and media persist under `data/`; preserve it to retain work. `CLIPFORGE_DATA` changes the storage directory. Uploaded photos/logos are normalized and bounded; assets are restricted to their owning project. Default asset limits: 25 per project, photos 20 MB/4096 px, logos 10 MB/4096 px, B-roll 100 MB/10 minutes, music 30 MB/20 minutes. Limits are displayed before selection and fetched from the backend. Oversized files are rejected in the browser before upload and checked again by the server. A failed B-roll upload's error stays in its own panel, with a dismiss action; it does not appear in Branding.

## Public-platform imports

yt-dlp **2026.10.21** with curl_cffi **0.16.3** handles supported public HTTP(S) video sources. YouTube, social short links and direct MP4 imports share the same pipeline. Browser-compatible TLS is used for social sources; redirects retain public-address validation. Private/local destinations, playlists, live streams and unsupported restricted content are rejected. No account credentials or private browser cookies are read.

Connection resets on public browser-transport GET/HEAD requests receive up to three attempts while retaining the session, with real reconnect feedback. The complete import can restart up to three times if a later stage still resets; a resolved TikTok short URL is retained across these restarts. POST requests and HTTP access denials/rate limits are not replayed by this recovery. Public-address validation runs again before each retry and redirect. A supported extractor does not guarantee every video is accessible. Private/login-only, deleted, region-restricted, DRM or bot-blocked content may fail; upload the local file instead.

After the request-recovery update, the supplied Instagram reel and original TikTok short URL **both imported through the running app**, with audio, working source previews/thumbnails and rendered MP4 test clips. Import times in that check were about 8.25 and 15.94 seconds respectively, not speed guarantees. Earlier checks failed; intermittent or persistent site restrictions can still prevent other attempts. Facebook/Bilibili/Dailymotion end-to-end import is not established by these two results. The fact that regular Edge opens a URL does not guarantee automated downloader access.

## Performance and hosting

Speech recognition and rendering run on the backend computer, so changing browsers does not speed them up. Urdu/Hindi/native output choices use the stronger multilingual small model. Roman Urdu uses small for Urdu/Hindi/auto speech; explicit English retains the lighter standard model before translation. Original Fast uses tiny, while Original Quick/Balanced/Accurate use base unless configured. Model labels show the actual choice. Cached speech models load locally before trying a network download.

New imports default to **Quick**, which batches the same multilingual model used by Balanced. Balanced keeps sequential context; Accurate uses a larger decoding beam and takes longer. Fast remains a separate lower-accuracy tiny-model choice for Original captions. One warmed 24-second speech sample took 6.405 seconds in Balanced and 4.757 seconds in Quick on this machine. Batched context/VAD can change recognition; this is not an accuracy or universal speed guarantee. Existing projects retain their saved mode. Set `CLIPFORGE_FAST_BATCH_SIZE=1` to lower batching memory (default 4, maximum 8).

For sources longer than three minutes, visual analysis reads encoded keyframes at their actual presentation times, with a bounded visual scan, while measuring the full audio energy/silence timeline. Fine scene cuts between keyframes can be missed, and unscanned intervals have no invented visual measurements. Short sources retain two-frame-per-second analysis. The actual 47:16 user source completed analysis in **52.585 seconds**, where its earlier full decode had timed out after 900 seconds. This measures analysis, not downloading, transcription or rendering every clip.

**Processing quality** is visible beside the import languages: Quick 480p, Balanced 720p or Full HD 1080p. It controls source download and clip export quality; lower resolution processes fewer pixels. The existing Full HD default remains. Changing quality cannot restore detail missing from a low-resolution source. Two render workers and a separate transcription queue bound local concurrency; set `CLIPFORGE_RENDER_WORKERS=1` on smaller machines. GPU execution is not configured. Processing 100 clips or long video still takes real compute time.

Clip requests are maximum quantities. The result explains how many new clips could be selected, how many actual candidate ranges failed the score rule, and how many overlap/repeat already selected moments. Several ranges can describe one moment, so candidate counts are not additional exportable clips. A request for 30 with only four qualifying distinct moments produces four; it does not lower your threshold or pad the result with duplicates. Existing source videos and clips remain intact.

This is currently a local application. Keep servers on loopback while testing. Vercel alone cannot host the current long-running Python/FFmpeg jobs and persistent local SQLite/media storage; a separate persistent backend/worker host and production limits are needed. Durable distributed jobs, load testing, quotas, robust cancellation, GPU paths and desktop packaging are unfinished. Interrupted jobs become retryable errors after restart. Large uploads are buffered by the Next proxy; the configured 2 GB cap is not a resumable-upload or low-memory guarantee.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest tests --ignore=tests/browser -q
node node_modules/typescript/bin/tsc --noEmit
npm run build
# With the completed frontend and backend running:
$env:CLIPFORGE_BROWSER_CHANNEL='msedge'
# Avoid an Edge-only document.fonts.ready hang in optional layout screenshots.
$env:PW_TEST_SCREENSHOT_NO_FONTS_READY='1'
node node_modules/@playwright/test/cli.js test
# Real-model/media checks (cached samples/models are required):
.\.venv\Scripts\python.exe -m scripts.verify_roman_speech --mode fast --auto-language
.\.venv\Scripts\python.exe -m scripts.verify_translation
```

Latest complete verification (1 November 2026): **454 backend tests and all 32 Microsoft Edge scenarios passed**, with zero failures/errors/skips. Production build and TypeScript checking passed. Real imports/uploads, generation, Hindi/Roman Urdu captions and restoration, English-to-Urdu translation, neon exports, ratio/shared edits, branding, layers, audio, transitions, playback/download, privacy and deletion were verified. Desktop/mobile captures and actual MP4/WebM files were checked. The original source and four ready clips remain unchanged. See [VALIDATION.md](VALIDATION.md) for exact reports, speed measurements, corrected failures and practical limits; [PROJECT_AUDIT.md](PROJECT_AUDIT.md), [STUDIO_REFERENCE.md](STUDIO_REFERENCE.md) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) retain architecture, scope and attribution details.
