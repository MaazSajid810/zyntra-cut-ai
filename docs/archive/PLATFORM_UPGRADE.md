> Historical document before the frontend/backend split. Use the [current README](../../README.md) for folder paths and setup commands.

# Independent creator platform upgrade

## Current direction: October 28, 2026

The supplied dark/green clipping screenshots supersede the earlier white/blue theme below. Create now has a narrow source-preview/settings area, original ZyntraCut branding, sidebar and real progress. Metadata preview is separate from download/generation. Custom quantity and 3–180 second duration remain functional. Language choices reflect installed local support.

Uploads, imported projects, generation, playable previews and editing stay at `/dashboard?project=...`. Generated cards support score/time/duration sorting, manual downloads and confirmed individual/selected deletion. Cancellation keeps selection; failed deletions are reported. The compatibility full editor remains available.

Recovery reuses saved original speech, preserving strict settings and existing clips. Unsupported translation retains original captions with an explicit warning. Errors distinguish post-download processing failures from source-site restrictions. See `VALIDATION.md` for tested behavior and limits.

## Earlier implementation

User-provided screenshots establish four modules: Create (source import/recent projects), Explore (video discovery), Wizard (conversational operations) and Studio (new media). Preserve existing owned projects, effects, transcription, render and deletion APIs.

Implementation order:
1. Add original white/black/blue page shell and actual routes, reusing the working clipping editor rather than replacing it.
2. Create: real imports/uploads, custom count/duration, measured private-project statistics and recent projects.
3. Explore: actual public-video discovery with category filters, cached metadata and refresh. A relevance search is not a trending chart; only report measured view velocity when two observations exist. Fall back honestly on unavailable upstream data.
4. Wizard: explicit local command interpretation with a reviewable action plan using existing APIs. Do not present a rules-based parser as a general language model. Support clip generation, trim, captions, format, speed, voice and export preparation; unsupported instructions return a useful explanation.
5. Studio: real local PNG text designs and animated text/photo MP4s using Pillow/FFmpeg; owned persisted jobs and errors. Prompt-to-photorealistic image/video generation requires an additional generative model and is not simulated. Keep the user's free/local preference.
6. Verify ownership, failed jobs, actual file decoding/durations, navigation, create/import, command execution and responsive layouts. Preserve the full editor at its own route and a compatibility workspace for existing users/tests.

Explicit limits: no copied creator media, fake credits, sample projects passed off as results, invented trend counts, or claims that a caption cover erases burned-in text. Local Studio designs/photo motion are not generative footage. This stage is not full parity with every paid Kixy feature.

## Implemented architecture

- `/` and `/dashboard`: original white/black/blue Create page, count/duration, optional styling, real uploads/imports, private-project statistics/recent projects and confirmed deletion.
- `/explore`: category-filtered public YouTube relevance search plus private library. Results cache for an hour; forced refresh is bounded. View velocity requires comparable observations at least five minutes apart. Upstream/stale/blocked states are explicit; this is not a verified trending chart.
- `/wizard`: private saved conversation, local command parser, review-before-execute, actual generate/edit/render API calls, real preview/manual download and New chat. No arbitrary general-model claims.
- `/studio`: real PNG title designs and portrait text/photo-motion MP4s, queued owned jobs, styles, duration/size, optional photo, preview/download, project/editor handoff, confirmed deletion, bounded admission and interrupted-job recovery.
- `/editor?project=...&clip=...`: preserved full editor. `/workspace`: original workspace. Existing project formats and private APIs remain. Older browser checks now enter `/workspace`; new checks cover the platform routes.
- `backend/platform.py`: namespaced SQLite settings for jobs/chat/public discovery. Private uploads are never part of shared discovery. Studio videos become normal owned project records.

No dependency or heavy generative model was installed. Paid-style scene/image synthesis, arbitrary conversational AI, true burned-caption inpainting and full multi-source timeline parity remain outside the implemented local feature set.
