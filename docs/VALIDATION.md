## November 6, 2026: captions, dubbing and sound effects

- The complete backend suite passed 491 tests. An additional AV1 preview regression passed separately after being added. Production webpack build, TypeScript checking and the three deployment configuration checks passed.
- Three headless Microsoft Edge checks passed in 2.7 minutes: complete AV1 dubbed-video playback without clips, original/dub comparison and stale-caption protection; scheduled sticker/voice/clip workflows; and logo, watermark, B-roll, Sparkle sound preview/volume, transitions and real clip export. Test projects were removed.
- A private 569.301-second English upload had been decoded with a forced Punjabi source setting. Its original file and previous transcript were preserved. Actual source recognition produced 144 English segments with word timestamps. Offline Urdu dubbing then produced 73 fitted sentence groups and a complete 1920x1080 AV1/AAC MP4, with a measured duration of 569.301 seconds and a matching caption/audio fingerprint.
- On a real 24-second Urdu dialogue sample, batched decoding returned only one late segment. Independent decoding returned 13 segments across the sample. Regional Quick mode now uses independent decoding. This comparison checks speech coverage; names and exact wording still need review.
- Confident source-language mismatches are corrected before decoding. Uncertain mismatches stop with an actionable message. Repeated syllables and combining marks inside a token are rejected before saving captions or generating speech.
- Optional, MIT-licensed M2M100 INT8 translation is installed through a pinned, checksum-verified setup command. Selected simple positive/negative Urdu and Hindi meanings were tested. Translation quality varies; Punjabi and Sindhi examples included poor translations. Review translated meaning against the saved source text.
- Dubbing creates a full playable MP4 even when no clips exist. It retains supported source video streams, fits voice to adjacent sentence groups, caches translated drafts for retries and marks voice tracks stale after caption edits. The original video stays available. Speech is basic eSpeak synthesis; mouth movements and speaker identity stay original.
- Ten original synthesized sound effects share the same FFmpeg expressions for preview and export. Eleven dedicated checks verified preview access/ranges, real PCM energy, insertion time, silence outside the effect and MP4 duration. Volume and output-time controls remain available alongside background music.

# Validation record

## November 5: separate frontend and backend folders

Moved Next.js source, configuration, assets and browser tests into frontend/;
moved Python requirements, scripts and tests into backend/. Root now contains
README, third-party notices and gitignore, with current documentation and five
application screenshots in docs/. Older audits remain under docs/archive/.

Added backend/run.py for serving/setup/testing from the backend folder. Renamed
backend/platform.py to workspace.py to avoid shadowing Python's standard-library
platform module when running pip or the service inside backend/. Updated browser
fixture imports, Python executable resolution, font paths, environment examples
and Vercel Root Directory guidance. Existing root data/ was not relocated.

The isolated-checkout backend suite passed **465 tests in 182.87 seconds**.
Production frontend Webpack build, TypeScript and three deployment-configuration
checks passed. The frontend build script now uses the verified Webpack command.
After switching the local services to the new folders, **nine Microsoft Edge
checks passed in 2.5 minutes**, covering reconnects, navigation/mobile layout,
source metadata, actual upload/render/playback, Wizard editing and Studio PNG/MP4
creation/deletion. Frontend/API/font endpoints returned HTTP 200. Existing user
project records exactly matched their snapshot taken after the active job
finished; source storage was not moved.

The first custom pytest invocation failed because its requested temporary parent
directory did not exist; after creating that test-only directory, the complete
suite passed. No failed attempt is counted as a successful run.


## November 4: thumbnails, batch generation, captions and offline voice translation

- Final backend suite: **465 passed in 240.94 seconds**, no skips or failures
  (`artifacts/backend-final-all-nov4.xml`). Includes ten distinct real MP4
  exports, actual English-to-Urdu/Hindi/Spanish translation and eSpeak synthesis,
  sentence-slot audio timing, compositor sound effects, stale-voice rejection,
  guest ownership, missing-route fallback and background-job failures.
- Production Webpack build and TypeScript passed. A preceding Turbopack build
  lost its PostCSS child-process connection while long speech processing was
  also running; it was not counted as successful. The verified release is
  `.next-voice-nov4-webpack`; the previous frontend output remains intact.
- Seven distinct focused Edge scenarios passed across the recorded runs:
  three connection/retry cases, two generation-feedback/real-speech cases,
  thumbnail failure recovery, and the complete offline dubbing/render/original
  audio workflow. The first dubbing browser attempt failed on a transient
  proxied status GET reset while heavy recognition and the backend suite ran;
  the completed backend result was valid. The final isolated dubbing/thumbnail
  run passed both cases in 79.86 seconds
  (`artifacts/edge-dubbing-final-nov4.xml`). Failed runs were retained as evidence.
- Three deployment configuration checks passed. No Vercel deployment was made;
  a persistent public processing backend is still required.
- Two affected real YouTube discovery thumbnails were fetched successfully
  through the fixed-ID image path (480x360 JPEGs). An unavailable thumbnail
  keeps a usable source card with a readable fallback.
- The user's saved drama source and ready clip were preserved. A 24-second
  audio sample independently detected Urdu (0.862 confidence), whereas the
  saved project forced English recognition. The initial full Accurate/Auto
  diagnostic detected Hindi weakly (0.449) and produced repeated-token loops;
  it took 1548 seconds and was rejected, not saved over the user's transcript.
  A separate full Quick Urdu diagnostic was stopped without changing user data
  during the resource-heavy combined run. It is not claimed as a completed repair.
  Recognition now samples three windows for auto detection, resets prior-text
  context, rejects obvious repeated/unreadable output, and exposes a repair action.
  Exact wording still requires review; no recognition accuracy guarantee is made.
- The inspected machine has Intel HD Graphics 520 and 7.88 GB system RAM.
  Offline voices are basic synthetic eSpeak voices. Sentence timing is aligned;
  neural mouth animation and voice cloning are not implemented or advertised.
- Five reference screenshots were captured from the running app in a fresh
  isolated guest workspace. Studio rendered the sample title footage. No private
  user project, competitor media or account credential is included in them;
  each screenshot fixture was deleted through the application's API afterwards.


## November 2: interrupted connections and sidebar cleanup

The redundant Full editor sidebar shortcut was removed; clip editing and the
existing editor routes remain available. Its initial navigation/mobile check
passed (`artifacts/sidebar-cleanup-edge-20261101.xml`).

At diagnosis the dashboard, proxied health endpoint and backend all returned
HTTP 200, with no new saved user import matching the reported attempt. The
frontend had been restarted for the preceding menu update; a request interrupted
during that restart is a plausible cause of the screenshot, not proof that its
video URL was restricted. An isolated Edge connection-abort reproduction showed
the raw `Failed to fetch` message remained after a later successful projects
response (`artifacts/network-recovery-before-20261102.json`).

Browser transport errors now receive an actionable connection message. Project
refresh errors are kept separate from action errors: a recovered read clears
its warning while a real upload rejection remains visible. Import status polling
clears its transient error after reconnection and retains the accepted job ID.
Failed POST requests are not automatically replayed. No account cookie or
existing project was cleared.

Production build/TypeScript passed in a separate `.next-recovery` directory
while the main dashboard remained HTTP 200. **Five focused Edge scenarios
passed**, covering reconnect/recovery, preservation of upload errors, explicit
POST retry, accepted-job polling without duplicate submissions, navigation and
metadata rejection (`artifacts/connection-recovery-edge-20261102.xml`). Upstream
metadata/job-state/rejection fixtures are explicitly labelled and do not fake
download or generated video output. Backend code was unchanged; the preceding
454-test backend result is historical, not a rerun for this UI fix.

The initial actual-import check on preview port 3001 correctly received HTTP
403 from existing origin protection. After switching the verified release to
the allowed main port, the **real public MP4 import and playback test passed**
(`artifacts/connection-real-import-main-20261102.xml`). No origin check was
relaxed. The selected release is recorded in ignored local configuration for
future starts; original build output remains available for rollback.

## November 1: complete regression, clip-count feedback, speed and neon captions

The current production Next.js build and TypeScript check passed. The complete
backend suite passed: **454 tests in 133.52 seconds**, zero failures/errors
(`artifacts/full-final-backend-20261101.xml`). This includes real encoded
audio/video checks, import/fragment handling, language routes, speech timing,
caption sync, selection, recovery, privacy, assets, layers, effects, ratios,
batch settings, deletion and export. The complete **Microsoft Edge suite passed
all 32 tests in 380.604 seconds**, zero failures/errors/skips
(`artifacts/full-final-edge-20261101.xml`). It covers actual public-file import,
12 MB upload, generation, real speech/translation, Hindi/Roman Urdu restoration,
neon and batch exports, captions, branding drag, music/SFX, B-roll/photos,
transitions, timeline, playback/download, deletion/privacy, and desktop/mobile
layouts. Upstream UI metadata/rejection fixtures remain explicitly labelled;
they do not establish live access to every social-platform video.

Requests now report their actual selected count and explain a shortage against
the requested maximum. Quality-mode diagnostics count real candidate ranges,
score rejections, overlapping ranges and repeated content. Alternate ranges of
the same moment are explicitly not extra exportable clips. Regression tests
request 30, select four distinct qualifying stories, reject a weak/repeated
story, then prove a second request preserves those clips and produces zero.
The original user's 47:16 source has four ready clips; a read-only selection
audit found 127 score-qualified candidate ranges overlapping those four moments.
No threshold was silently reduced, source padded or user clip regenerated.

Long sources now measure visuals at encoded keyframes with actual timestamps,
with a 60-second visual scan budget, plus the full audio energy/silence timeline.
Short sources retain the dense two-frame-per-second method. A zero-budget test
proves missing visual measurements are not invented; sparse-interval tests
check actual timestamps and complete audio. Fine scene cuts between keyframes
can be missed. An actual read-only run on the user's 47:16.501 source completed
in **52.585 seconds** with 1,081 keyframe samples and 5,674 audio buckets; its
previous full-decode attempt recorded a 900-second timeout. This measures source
analysis, not the entire download/transcribe/render workflow. Evidence:
`artifacts/analysis-speed-20261101/report.json`.

New imports offer Quick batched speech using the same base/small model as
Balanced; contextual Balanced and Accurate remain available, and existing
project modes are preserved. A warmed 24-second source excerpt took **6.405s
Balanced / 4.757s Quick** with the same base model. Segment/word outputs differed,
so this does not establish equal recognition accuracy or universal speed.
Evidence: `artifacts/quick-speech-20261101/report.json`. The visible processing
quality choice controls both source download and clip export (480p/720p/1080p),
with the existing Full HD default preserved. No render-thread tuning or GPU
acceleration is claimed.

Neon glow and Neon word highlight are available in import presets and the clip
editor, including shared edits. Actual MP4 pixel tests prove the pink glow and
an active green word moving at saved speech timestamps. Edited/translated text
without matching word timing falls back to a readable glowing phrase. The final
focused analysis/neon/speech tests also passed (25 tests,
`artifacts/finishing-verified2-20261101.xml`); these are included in the complete
454-test result rather than added to its count.

The first completed browser run exposed a regression for manually entered
Hindi/Urdu captions with no detected speech language: route validation fell back
to Original even when native text could be retained/romanized locally. This is
fixed without guessing or changing the saved speech language. New API tests
cover Hindi retention, Hindi/Urdu romanization, immutable source snapshots and
unchanged clip ranges for both missing/Auto source labels. Known unrelated
languages and unknown Latin text still require a real translation route.
All 89 focused language/romanization/recovery tests passed before the complete
454-test rerun. A new browser assertion was also corrected to locate Speech
recognition by its combobox role/name; the control was present and selected.

An earlier browser attempt hung in Playwright's optional screenshot font-ready
wait after its import assertions completed. Its trace was retained under
`artifacts/edge-font-wait-initial-20261101`. The completed runs use
`PW_TEST_SCREENSHOT_NO_FONTS_READY=1` for layout captures. Actual exported
caption fonts/pixels and aligned-word timing retain their separate FFmpeg
tests; no golden-image font-match claim is made.

Final integrity checks found both running services at HTTP 200. The original
47:16 source's project payload hash and 1,013,869,119-byte source are unchanged.
All four existing ready exports remain readable 1080x1920 videos with audio;
the separate new neon browser export is a valid two-second video with audio.
Evidence: `artifacts/final-integrity-20261101.json`. No user clips were deleted,
replaced or padded. The app remains at http://127.0.0.1:3000/dashboard.

## November 1: missing temporary download fragment

The reported `WinError 2` was reproduced from the application's actual log. The
failure was in its progress callback: `is_file()` succeeded for a yt-dlp fragment,
then yt-dlp renamed/deleted that fragment before the second `stat()` call. This
was a local time-of-check/time-of-use race, not evidence of a private video or a
missing FFmpeg executable.

Download-size accounting now reads each entry's metadata once and skips only
`FileNotFoundError` for disappearing entries. Other disk errors still propagate;
regular file sizes and the existing 2 GB limit remain enforced. The downloader's
public URL/redirect checks, concurrent fragments and access restrictions remain
in place. A surviving missing-fragment error has an actionable local-file
message without exposing an internal file path or attributing it to privacy.

**75 targeted tests passed** (`artifacts/fragment-regression-20261101.xml`):
fragment disappearance before/during metadata inspection, actual encoded video
probe, size-limit enforcement, permission-error propagation, imports, redirect
validation, privacy and source preview. The updated backend was restarted while
there were no active imports/renders; backend health and the frontend returned
HTTP 200.

Live verification downloads the exact failed user-supplied public YouTube URL at
1080p into an isolated ignored test-artifact directory. It does not change the
user's failed import record, projects, transcript or requested clip count. The
result is recorded separately after complete video/audio validation.

**Live verification passed**: the exact failed URL downloaded and merged to a
1,013,869,119-byte MP4 at **1920 x 1080**, duration **47:16.501**, with audio.
Full download/merge, container probe and a real three-second audio/video decode
succeeded (575.57 seconds including network transfer). Evidence:
`artifacts/fragment-live-20261101/report.json`. No transcription was started;
this does not claim captions/clips were generated for the user's failed job.
Existing failed-job history remains unchanged; retry the same link through Create.


## November 1: ratio, batch edits and native caption controls

Production Next.js build and TypeScript passed. Focused language, recovery,
Hindi, recognition-options and shared-settings tests: **80 passed**
(`artifacts/nov-language-smoke.xml`). Native Gurmukhi, Bengali, Sindhi, Pashto and
Spanish caption exports: **5 passed**, real FFmpeg MP4 pixels and compatible font
selection (`artifacts/nov-native-render.xml`). Existing Microsoft Edge scenarios
for source metadata/settings submission and actual batch-edit/render/download:
**2 passed**. Deployment-origin validation: **3 passed**. This is targeted
verification of the new changes, not a repeat of the earlier entire suite.

Actual local English-to-Spanish text translation returned translated sentences
and retained source segment start/end. The installed incoming pair is reported
through `/api/languages`. Other uninstalled cross-language routes retain original
captions with a notice. Recognition tests do not establish word-perfect accuracy
for every language or dialect. Video dubbing is not implemented.

Both local services returned HTTP 200 and Create exposes the ratio and Punjabi
options. GUI Microsoft Edge launch was rejected by automatic review with
`blocked by policy`; the app remains available at http://127.0.0.1:3000/dashboard.
The separate headless Edge regression scenarios above succeeded.

GitHub source preparation and Vercel configuration were added. Remote publishing
still needs valid GitHub sign-in; the stored credential returned HTTP 401 and the
device-auth code expired without completion. Vercel CLI reports logged out, and
no persistent public HTTPS processing-backend origin has been supplied. No
repository upload or production deployment is claimed. No ads were integrated,
following the user's clarification.

## Dark clipping workflow — October 28, 2026

- Create follows the latest dark/green reference with original ZyntraCut branding. Real source metadata precedes generation; language, duration and custom quantity remain connected to actual APIs. Imported/uploaded projects, processing, source playback, clip gallery, previews and editor remain on Create. The standalone full editor is preserved.
- `POST /api/source-preview` requires a private guest session and reads metadata only, with public-request/redirect validation. It creates no media download, project or transcript. Unknown metadata remains unknown. The supplied public YouTube URL returned its real title, thumbnail and 1,205-second duration; a preview cannot guarantee later download access.
- Unsupported local translation keeps original words/timestamps and detected speech language, while saving the requested choice and showing a notice. Recovery reuses saved speech without another download/ASR pass, preserves strict rules and existing clips, and rejects missing/escaped files or active work. Post-download processing errors no longer append misleading private-video advice.
- A failed import was recovered from 1,055 saved source segments with a private backup. Its 84 score, 43 requested clips and 60–90-second range were preserved; zero candidates qualify at those rules. The result reports a 41-clip duration capacity and user-controlled alternatives. No score or transcript was fabricated; selection rules were not silently relaxed.
- Generated cards support score/time/duration sorting, manual downloads and confirmed individual/selected deletion. Cancellation retains selection; partial failures remain visible. Mobile actions wrap and cards use one column. Thumbnails are source posters, not invented per-clip scene images.
- **Complete backend suite: 392 passed in 462.39 seconds**, zero failures/errors (`artifacts/dark-full-backend-20261028.xml`). Includes real FFmpeg exports, recovery, translation, word timing, selection, preview validation, ownership, effects, audio, layers, duration and deletion. Focused source-preview checks: 23 passed; focused recovery/adjacent checks: 121 passed. Production Next.js build and TypeScript checking passed.
- **Complete Microsoft Edge suite: all 30 passed in 289.24 seconds**, zero failures/errors (`artifacts/dark-full-edge-20261028.xml`). Checks include actual source download/upload, transcription, Roman Urdu/Hindi/English translation, real clip playback/export, timed media/audio layers, desktop/mobile layouts, privacy and deletion. New tests verify that metadata creates no import until confirmation, custom count/language/duration reach the API, source-capacity feedback is visible, metadata failure offers an explicit import retry, Home returns to Create, and surviving previews remain playable after partial deletion.
- Earlier checks exposed mobile action overflow (fixed globally), stale one-step-import test assumptions (updated), ambiguous status locators (scoped to generation feedback), and successful deletion leaving surviving previews without a source (fixed and regression-tested). An initial preview timeout occurred during the concurrent CPU-heavy backend suite; its render completed and subsequent real playback checks passed. The final complete suites above passed after correction.
- Real metadata UI captures: `artifacts/live-source-preview-1440-20261028.png` and `artifacts/live-source-preview-390-20261028.png`. Actual clip-gallery captures: `artifacts/dark-clips-1440.png`, `artifacts/dark-clips-768.png`, `artifacts/dark-clips-390.png`. Metadata fixtures and injected rejection responses in isolated UI tests are labelled explicitly; live source metadata and actual exported video files were verified separately. Both local services remain running; the Create page was opened in Microsoft Edge.
- Limits: no guaranteed virality, universal site download access, arbitrary-language translation, live clipping/scheduling, general conversational AI, photorealistic prompt footage, generated AI music or true burned-caption inpainting. No paid service, new dependency or heavy generative model was installed.


## Independent Create / Explore / Wizard / Studio - October 26, 2026

- Implemented the original screenshot-inspired white/black/blue creator platform at `/` and `/dashboard`, `/explore`, `/wizard`, `/studio`. Existing private-project APIs, assets and data formats are preserved. The full editor supports direct owned project/clip links at `/editor`; the earlier full workspace remains at `/workspace`.
- Create uses real file uploads/public-link imports, count/duration controls, actual private-project statistics, recent projects and confirmed deletion. Explore supports category-filtered public YouTube relevance search, cached/stale/error states, private library and import handoff. A real live request returned **12 metadata records with HTTP 200** (`artifacts/platform-live-discovery.json`). It is not a verified trending chart. First observations never invent view velocity; later comparable observations must be at least five minutes apart.
- Wizard interprets explicit supported local commands, validates owned context, shows a reviewable plan, then uses real generate/edit/render APIs. Conversation history is private and persisted. A real clip changed caption style, rendered and played; unsupported scene-generation requests produced a useful error rather than a fake response.
- Local Studio creates real PNG designs and animated text/photo portrait MP4s, with actual queued/running/ready/error states, bounded job admission, interrupted-job recovery, preview/manual download, editor handoff and deletion. Confirmed tests decode/probe the outputs, check guest isolation, and restore a preview after an injected deletion rejection before retrying real deletion.
- **Complete backend suite: 341 passed in 104.21 seconds**, zero failures/errors (`artifacts/platform-full-backend.xml`). **Complete Microsoft Edge suite: all 28 passed in approximately 5.2 minutes**, zero failures/errors (`artifacts/platform-full-edge.xml`). Production Next build and TypeScript checking passed. The browser suite includes both the new platform and preserved editor workflows, real exports, custom durations, guest ownership, uploads/imports, individual/bulk/project deletion, captions/translation, motion/audio/layers and responsive 1440/768/390 layouts.
- Regression checks found and fixed short-source selection rejecting complete speech followed by a short trailing pause. Requested duration bounds still apply when the source is long enough; explicitly reported short-source adaptation now preserves complete speech without padding. Added coverage for both Quality and Explore-all modes. Added pytest configuration so old Windows-locked artifact folders are not collected as source tests.
- Earlier development failures were fixed: an incomplete test fixture lacked clip status; a Wizard error assertion also matched Next's route announcer; deletion-rejection preview restoration was added. The complete final suites above passed after these corrections.
- Evidence includes `artifacts/wizard-real-export.mp4`, `artifacts/studio-local-motion.mp4`, `artifacts/platform-create-1440.png`, `artifacts/platform-create-390.png`, and corresponding Explore/Wizard/Studio responsive captures. Mock discovery metadata and 429/409 responses in UI tests are explicitly labelled test fixtures; live metadata retrieval and actual media creation are verified separately.
- Limits: no general conversational model, photorealistic prompt-to-image/video generation, true burned-caption inpainting, moving-subject tracking or arbitrary multi-source timeline composition. Local Studio is title design/photo animation, not simulated AI footage. No new dependency/heavy model, Kixy service, paid provider, copied creator media, login requirement or credit system was introduced. These results establish tested behavior, not complete paid-feature parity or guaranteed virality/import availability.

## Custom quantity and duration - October 25, 2026

- Link import now exposes the custom clip count and duration before optional styling. Both import and uploaded-project generation submit `clip_count`, `auto_count`, `min_duration` and `max_duration`. Duration presets are 15-30, 30-60 and 60-90 seconds; custom ranges allow 3-180 seconds. Counts remain 1-100, or Auto. Invalid ranges block generation and are rejected by the backend. Inputs retain blank state for editing instead of silently replacing it with zero.
- The backend already supported quality-mode duration bounds. This follow-up also enforces bounds in Explore all, including an oversized first transcript segment, and records the requested range in generation metadata. The legacy helper's callers without duration arguments retain their original target behavior. Count remains a maximum; no weak/duplicate footage or padding is inserted just to fill it. Short-source adaptation remains explicit. Ranges describe source seconds; playback speed changes export duration.
- **41 backend tests passed in 11.12 seconds** (`artifacts/custom-duration-backend.xml`), covering both selection modes, short sources, 8-12/16-24/60-90 ranges, persisted counts/bounds, rejected ranges without mutation, import schema, existing selection/measurement behavior and actual media processing. Production build with TypeScript checking passed.
- **All 5 focused Edge tests passed in 58.3 seconds** (`artifacts/custom-duration-edge.xml`). A real encoded 24-second source with an explicitly supplied test transcript generated two actual MP4 clips within 8-12 seconds; exported duration and audio were probed, and count/bounds survived reopening. Import preset/custom validation and POST values, existing Auto quantity, timeline/export and desktop/mobile behavior passed. This is a focused regression, not a new complete browser/backend suite run. Artifacts include `artifacts/custom-duration-export.mp4` and `artifacts/custom-duration-mobile.png`.

## Preview-first reference workflow - October 25, 2026

- Generated projects now open in a clip-review gallery. The four workflow steps connect import, analysis, review and editing. Selecting a preview does not enter the editor or start a download. Ready clips use their actual rendered media; unrendered clips are labelled source-range previews. Explicit editor entry, return to results and confirmed per-clip deletion use the existing private APIs.
- Link customization is collapsed initially. Count, quality, caption and rendering settings persist when collapsed and are submitted through the existing import endpoint. Optional-setting tests deliberately inject a 429 to verify error handling, not to simulate downloading. The separate public MP4 import test downloaded and played real media successfully.
- Production build and TypeScript checking passed. The complete Edge run passed **22 of 23 tests in 6.5 minutes** (`artifacts/preview-workflow-edge.xml`). The Generate-100 recovery test timed out on a five-second assertion while real analysis was still running. After allowing up to 60 seconds for actual processing, its targeted rerun passed **1/1 in 23.5 seconds** (`artifacts/preview-workflow-recovery.xml`). All 23 scenarios have successful coverage across these runs; no zero-failure contiguous 23-test batch is claimed.
- Coverage includes real preview playback, no automatic downloads, gallery/editor navigation, auto quantity, trim/Undo/Redo, saved timed photo layers, encoded MP4/audio, individual/bulk deletion, guest isolation, existing import options, Hindi/Roman Urdu, actual English-to-Urdu translation, stickers, voice comparison, watermark/logo/B-roll/music/transitions, and responsive layouts. Desktop/mobile gallery captures are `artifacts/clip-review-desktop.png` and `artifacts/clip-review-mobile.png`.
- Backend code and model selection were unchanged in this workflow update; the preceding 311-test backend baseline below was not rerun. This does not add the reference product's advertised semantic video search, speaker tracking, automatic B-roll or social publishing.

## Project audit, measured ranking and visual editor - October 25, 2026

- Inspected the existing Next.js/React/TypeScript frontend, FastAPI routes, SQLite payloads, private guest ownership, Whisper caches, subtitle/translation pipeline and FFmpeg rendering. Hardware/encoder observations and ordered work are in `PROJECT_AUDIT.md`. No project migration or framework replacement was performed.
- Added cached measurements from actual decoded source media: half-second audio RMS levels and threshold silence, sampled 2 fps visual differences/scene-change candidates, and a waveform bounded to 1,200 buckets. If audio ends early, trailing silence stays on the video timeline. These are supporting measurements, not emotion recognition, face tracking or calibrated view probabilities.
- Quality ranking uses original source speech when available, preserves transcript sentence boundaries, rejects overlap/repeated content and cannot rescue a weak hook merely with loud/active footage. Auto quantity returns only qualifying distinct candidates up to 100. Duration bounds are validated; short-source minimum duration adapts. Analysis locks conflicting edits/deletion and uses an explicitly reported transcript-only fallback if measurement fails. Cache reuse and guest isolation are covered.
- The selected-clip workspace now contains a source/final player beside contextual tool panels, source range drag/keyboard trim, source-range movement, caption seek blocks, waveform, zoom, timed photo/B-roll movement/resize, music coverage and gesture-based Undo/Redo. Save/Apply & render uses the existing export path. AI settings fold after candidates are created; real results remain visible and settings can be reopened. Generate is above optional settings. The clip library scrolls horizontally.
- Regression checks identified missing Download/audio-comparison actions in the first player integration and an inherited desktop grid that constrained the new editor. Restored both actions, exclusive playback and full-width desktop layout. Old-layout assertions were updated to test player/properties alignment and timeline placement. An exact-name Auto test exposed a verbose accessible count label; the input now has an explicit accessible name.
- Windows project deletion now releases preview media, stages the directory atomically, restores it if SQLite deletion fails, and privately retries cleanup held by an open response. Startup restores a staged project if deletion did not commit. Tests cover locked staging, rollback, committed cleanup and crash recovery. The database failure in that test is injected deliberately; user source files remain intact.
- Final complete backend regression: **311 passed in 215.93 seconds**, zero failures/skips (`artifacts/editor-release-backend.xml`). The final production build and TypeScript checking passed. Focused final media-analysis/deletion tests also passed (`artifacts/editor-analysis-final.xml`, `artifacts/editor-deletion-final.xml`).
- Final Edge validation: the latest full batch passed **21 of 22 scenarios in 11.3 minutes**. The sole failure was a screenshot/font-capture timeout in the mocked import-error case after its functional assertions. Its dedicated rerun passed **1/1 in 14.7 seconds** with animations-disabled screenshots and a 180-second scenario budget. All 22 scenarios therefore have successful coverage across full/focused runs; no clean contiguous 22-test batch is claimed. Quality-analysis and Roman-script timing checks also passed together in a focused run. Approximately 580 MiB free memory was measured during the slow batch. Screenshot capture adjustments do not disable exported video animations. Final TypeScript checking passed.
- Actual Edge-driven FFmpeg exports verify drag trim, one-gesture undo/redo, photo output timing, save/reopen, a playable MP4 with approximately 2.5-second duration and retained audio. Evidence includes `artifacts/visual-timeline-export.mp4`, `artifacts/visual-editor-desktop.png`, `artifacts/visual-timeline-mobile.png` and `artifacts/reference-editor-desktop.png`. Responsive checks cover 1600/1440/1024/768/390 pixel layouts.
- Remaining scope: arbitrary multi-source timelines, split/ripple/reorder, keyframes, moving-subject tracking, semantic/emotion models, silence removal with exact timestamp remapping, durable cancellable workers and tested GPU encoding. No controls for these are presented as working.


## Photo layers and upload limits — October 24, 2026

- The reported "Filler exceeds the 100 MB limit" was a B-roll upload exceeding its existing size cap. The cap remains 100 MB. Asset pickers now load limits from the backend, show them before selection, and reject oversized files before upload. Server checks remain in place. Errors stay beside the relevant picker rather than appearing in unrelated tabs; users can dismiss them. Save/render is disabled during an asset upload.
- Added a separate photo layer for existing video projects: PNG/JPEG/WebP, up to 20 MB and 4096 pixels per side. Uploads normalize to PNG with EXIF orientation applied. Source start/end is unchanged; photo timing uses output seconds. Users can drag the photo, use arrow keys/X/Y controls, change size/opacity, or select full-frame contain/cover. Original source audio continues and captions render above the photo. Channel logos remain a separate 10 MB asset. Standalone image-to-video projects are not implemented.
- TypeScript checking and the production Next build passed. The final complete backend suite passed **298 tests in 228.54 seconds** (`artifacts/photo-final-backend.xml`). This includes real encoded PNG/JPEG/WebP uploads, JPEG orientation, corrupt-image rejection, ownership and reference validation, upload boundaries, timed FFmpeg exports, decoded pixel/opacity checks, contain versus cover, audio frequency and duration checks.
- The final complete **Microsoft Edge suite passed all 20 tests in approximately 3.8 minutes**. The new photo test checks an actual 101 MiB B-roll selection produces no upload request, its error stays out of Branding, uploading disables rendering, real photo upload succeeds, dragging/keyboard placement persists, and overlay/full-frame exports play. The existing combined-layer test now also renders a photo alongside B-roll, logo, watermark, music, effects and captions. Layout checks cover 1440, 768 and 390 pixel viewports.
- Inspected actual exported frames and the mobile photo panel. Evidence: `artifacts/photo-overlay-browser.mp4`, `artifacts/photo-full-browser.mp4`, `artifacts/photo-overlay-frame.png`, `artifacts/photo-full-frame.png`, `artifacts/photo-editor-mobile.png`, `artifacts/photo-panel-mobile.png` and `artifacts/photo-formats-final.xml`. Only isolated test projects were removed. Updated frontend and backend are running locally.

## Live social import recovery — October 24, 2026

- Reproduced the user's current Instagram reset in the running backend log. Verified HTTPS checks showed intermittent responses: the same public host sometimes responded while another connection reset. Standard requests, forced HTTP/1.1 and IPv4/TLS checks did not establish a universal transport fix.
- Added bounded recovery at the failing browser-transport **GET/HEAD request**, preserving its session instead of only restarting all extraction work. A verified TikTok short-link redirect is retained for a subsequent whole-import attempt if a later request resets. Real reconnect state is sent to the existing processing card. Redirect and retry destinations are validated again; certificates remain verified. HTTP denials/rate limits and POST requests are not replayed by request recovery.
- **47 import tests passed in 22.02 seconds** (`artifacts/request-reset-tests.xml`): actual downloaded fixture bytes, bounded recovery, no POST replay, no HTTP-error retry, DNS revalidation, public redirects, retained short-link targets, private guest ownership and real API import persistence.
- Final complete backend regression: **288 passed, zero failures/skips, in 125.31 seconds** (`artifacts/import-recovery-all.xml`). This also executes the previously pending offline speech-model cache unit test. **Two targeted Microsoft Edge checks passed in 22.5 seconds** after the backend change: real external MP4 import/playback and unsafe-local-link rejection. The earlier full 19-test Edge suite remains the broader UI baseline; no frontend source changed in this recovery update.
- The **running Next/FastAPI app** imported the user's exact TikTok short URL `https://vt.tiktok.com/ZSgmnSyeU/` in **15.94 seconds** and Instagram reel `https://www.instagram.com/reel/DegREppNbu4/` in **8.25 seconds**. Both sources had audio at 720×1280. Source byte-range requests returned 206 with 1024 bytes and posters returned 200. Each imported source produced a playable, inline MP4 range export. These are test clips, not a claim that this particular check ran AI highlight detection. Only this script's temporary projects were deleted.
- Evidence: `artifacts/social-recovery-live-api.json`, `artifacts/recovery-tiktok-preview.mp4`, `artifacts/recovery-instagram-preview.mp4`; reproducible command: `python -m scripts.verify_social_recovery`. Source durations were 18.877007 seconds (TikTok) and 5.453832 seconds (Instagram). Earlier failure records below remain historical and are superseded for these exact successful samples.
- A downloader restart was performed only after checking there were no active project/import jobs. Existing user sources/clips were preserved. The updated backend is running. Old failed job records remain errors until the link is submitted again; results are not retroactively marked successful.
- This is recovery from intermittent reset failures, not a bypass of private videos, login, DRM or bot challenges, and not universal platform availability. Facebook/Bilibili/Dailymotion end-to-end behavior is not proven by the TikTok/Instagram results.
- The earlier public Facebook sample was also retried. Its connection progressed to extraction, but yt-dlp returned **Cannot parse data**; no Facebook download success is claimed. This is a separate unresolved extraction failure, not proof that the user's specific Facebook video would work.

## Latest studio layers, translation and synchronization — October 24, 2026

This section supersedes older scope descriptions below. Current implementation and remaining CapCut/DaVinci-inspired editor work are tracked in [STUDIO_REFERENCE.md](STUDIO_REFERENCE.md).

- Full backend run: **280 passed in 164.26 seconds**, no skipped translation tests (`artifacts/studio-final-backend.xml`). A subsequently added unit test for cached-model loading was not separately executed after terminal approval review became unavailable; real speech loading through the new helper was exercised in the final Edge suite.
- Final production build passed. **All 19 Microsoft Edge tests passed in approximately 4.1 minutes**, including real upload/manual clip creation, generated preview, MP4/WebM/SRT download, native Hindi/Roman switches, independent English speech to Urdu translation, privacy, clip deletion, and responsive layout checks.
- Twelve media-layer tests cover actual logo pixels/opacity/position, text watermark defaults/opacity, B-roll output intervals and original speech preservation, fade/white transitions, music and three synthesized sound effects. The combined Edge workflow uploads and positions a logo, adds text/B-roll/music/SFX, selects cinematic filtering and fade, adjusts caption sync, renders a playable MP4, and checks mobile overflow. Actual output was visually inspected.
- A delayed-audio fixture verifies that an initial 0.8-second gap is preserved in transcription audio and becomes approximately 0.4 seconds at 2x export speed. Positive/negative caption offsets, boundary clamping, matching SRT/VTT and unchanged branding timing are covered.
- Real English speech was transcribed and exported into Urdu, Hindi, Roman Urdu and English MP4/SRT files. Tokenizer space markers initially leaked into Urdu/Roman output; normalization fixed the marker leakage and caption wrapping. Updated output frames were inspected. Native Urdu/Hindi audio both passed the fresh automatic Roman Urdu export check after timeline normalization.
- Translation is not word-perfect. A real negative statement lost its negation in the translation model. The application keeps original text beside translated captions and flags possible missing negation for review; it does not invent a corrected translation or claim complete semantic validation. Recognition and Roman spelling errors also remain possible.
- Full browser testing found a B-roll numeric-step mismatch blocking manual clip form submission. The input constraint was fixed and the complete manual-create/render/download workflow passed afterwards. A run conducted while build files were being replaced was discarded; the final suite ran against a freshly started completed production build.
- TikTok short URL `https://vt.tiktok.com/ZSgmnSyeU/` still reset on the live retry. Instagram's supplied reel imported in the earlier live API check; Facebook remains unverified/unfixed. These results do not establish universal platform support.
- Both local services were started on loopback for the final tests. A later terminal escalation failed because **automatic approval review hit a usage limit**, not because the action was judged unsafe. No new visible Edge launch, extra cache-unit run or post-limit runtime check is claimed.

## Regular Edge works without VPN: follow-up still pending — October 24, 2026

- The user confirms the public links open in their regular Edge browser with no VPN/proxy extension. Windows/environment proxy checks found no configured proxy. These facts do not establish an internet-wide outage; the regular-profile versus downloader/fresh-browser difference remains unresolved.
- Isolated Edge with HTTP/3 disabled and verified HTTPS requests using Edge, Windows Chrome and Firefox profiles still reset on the tested TikTok/Facebook URLs. System and HTTPS DNS gave matching Instagram/Facebook addresses; TikTok CDN addresses varied, which alone does not demonstrate DNS poisoning. Diagnostics: `artifacts/social-edge-http2.json`, `artifacts/social-browser-profiles.json`, `artifacts/social-dns-comparison.json`. No private browser cookies, login sessions or profile history were read.
- The new TikTok link is `https://vt.tiktok.com/ZSgmnSyeU/`; its live download has not been verified in this follow-up. The repeated Instagram link is the previously successful reel `https://www.instagram.com/reel/DegREppNbu4/`. Facebook remains independently unverified for the user's exact video. Meta ownership does not make successful Instagram extraction proof of working Facebook extraction.
- Bilibili and Dailymotion appear in the official yt-dlp supported-sites list, and the application uses its generic public-link extractor pipeline. That is compatibility coverage, not evidence that every URL or an end-to-end clip export currently works. Separate actual downloads/transcription/preview/export checks remain necessary.
- The next isolated browser diagnostic did not execute because automatic approval review hit a usage limit. This was a review infrastructure failure, not an unsafe-action determination. No alternate execution path was used to bypass the failed review. Subsequent live download checks remain pending. Only the retry-message punctuation was corrected on disk; no new platform fix is claimed from that edit.


## Social import transport update and live reset diagnosis — October 24, 2026

- Upgraded the project virtual environment from yt-dlp 2026.8.19 to **2026.10.21** and added **curl_cffi 0.16.3**, cffi 2.1.1 and pycparser 3.12. Updated requirements/lock; pip check reports no broken requirements. Social URLs receive a browser TLS profile while ordinary sources keep normal transport. No browser cookie database, login or private credentials were used.
- Added a guarded curl transport: internal libcurl redirects are disabled; every destination is validated before sending, redirect counts are bounded, POST-to-GET behavior for 303 is preserved, and credentials are stripped across origins. Existing Requests protection remains. Connection resets get at most three total attempts and measured retry status; access denials such as 403 do not loop. Reset messages distinguish connectivity from private/login-only videos.
- **All 260 backend tests passed in 99.39 seconds** (`artifacts/social-import-backend.xml`). This includes new real browser-transport downloads, relative/303/private redirects, redirect loops, transient reset recovery with an actual downloaded MP4, retry limits, non-retried access denial, ownership and the existing media/caption pipeline. Earlier focused import/privacy checks passed all 63 cases. **All four targeted Microsoft Edge import tests passed in 25.9 seconds** (`artifacts/social-import-browser.json`), covering multi-platform payloads, failure recovery, real public MP4 playback and mobile processing status. No frontend code/build change was needed.
- Verified the exact Instagram reel `https://www.instagram.com/reel/DegREppNbu4/`: metadata exposed 13 formats; a real download produced a 5.453832-second **720×1280** video with audio (1,530,296 bytes). The restarted live app's guest-owned import API also completed it in 9.07 seconds, returned byte-range preview HTTP 206 and thumbnail HTTP 200. Its isolated test project was deleted afterward (`artifacts/social-live-api.json`). Some earlier attempts reset, so this is successful tested import, not a guarantee of uninterrupted site access.
- The exact TikTok short link `https://vt.tiktok.com/ZSgmRywNo/` still resets, including all three live API attempts (0 bytes). Its vm.tiktok.com and official www.tiktok.com/t/ routes were checked too; one resolved the real video ID before the video page reset. The upstream public Facebook sample also reset (`artifacts/social-facebook-probe.json`). The user's exact Facebook video link was requested but not supplied; it remains unverified.
- Normal Requests, curl browser HTTPS, and isolated Edge navigation all encountered errors on the affected social hosts, while YouTube returned HTTP 200. Edge results are recorded in `artifacts/social-browser-connectivity.json`. This suggests network/path/site-side rejection; the available evidence does not identify the ISP, firewall, region or platform policy as the sole cause. A downloader patch cannot be claimed to resolve the remaining TikTok/Facebook reset. Do not disable certificate verification or assume a reset means private content.
- A real W3Schools MP4 download/probe also passed after the update. The backend was restarted only after active projects/imports finished; no active user processing was cancelled. Both loopback services remain running with the updated backend.


## Hindi/Roman Urdu recheck: functional exports, accuracy and auto-detection limits — October 24, 2026

- This recheck is **partially successful, not an all-clear for recognition accuracy**. Summary: `artifacts/subtitle-recheck-summary.json`. No application code or user project was changed; both local services remain running. Verification scripts use isolated temporary projects and the cached, attributed public FLEURS Urdu/Hindi audio.
- **20 targeted backend tests passed** in 22.66 seconds (`artifacts/subtitle-recheck-backend.xml`): real transliteration libraries, script snapshots, edited-text protection, word alignment/fallback, guest ownership, recognition options and real Hindi font/ASS rendering. **Both Microsoft Edge tests passed** in 46.3 seconds (`artifacts/subtitle-recheck-browser.json`), checking selectors, real captioned previews, Hindi/Roman/original switching, SRT/VTT, range preservation and responsive layout. Browser transcript fixtures are explicitly manual; actual ASR is verified separately below.
- **Eight genuine speech-to-automatic-MP4 cases passed** with explicitly selected Urdu/Hindi speech language: two public input languages × Roman/Hindi output × Accurate/Fast modes. Evidence: `roman-real-speech.json`, `hindi-real-speech.json`, `roman-fast-tiny-real-speech.json`, `hindi-fast-small-real-speech.json` under artifacts. Accurate Roman uses base; Hindi uses small in both modes; Fast Roman uses tiny. These checks establish script, genuine speech timestamps, render and playable video/audio output, not perfect wording. Recognition and Roman spelling errors were observed against the reference text.
- Fast Roman on the Hindi sample had **one of two segments fall back to phrase captions** because word alignment was incomplete. The phrase text was present in the actual exported tail frame (`artifacts/roman-fast-tiny-hi-tail-frame.png`). Other reviewed frames include `roman-ur-frame.png`, `hindi-hi-frame.png` and `hindi-fast-small-hi-frame.png`. Hindi fonts displayed correctly.
- **Fast + automatic language detection failed the public Urdu sample**: it labelled the speech Hindi, emitted English/repeated sentences, and covered less than eight seconds, leaving no candidate clip. The diagnostic is retained in `artifacts/roman-fast-tiny-auto-real-speech.json`. This is an ASR/detection limitation, not a claim that English was successfully converted to Roman Urdu. The automatic Hindi case was not reached after this failure. Explicitly selecting Urdu/Hindi worked in the eight export checks; users should review/edit the transcript before exporting. Fast auto cannot be described as reliable on this evidence.
- Extended `scripts.verify_roman_speech` with `--mode`, cached `--model` selection and `--auto-language`, separate reports/SRT/frames, actual timing fallback counts and fail-fast structured diagnostics for an unexpected zero-clip speech fixture. Initial Fast assertions wrongly required a native-script intermediate and every output segment to retain word timing; these were corrected to allow genuine Latin ASR and the existing documented phrase fallback, with fallback counts reported. The automatic-language failure remains reported as a failure.


## Individual and selected clip deletion in the library — October 24, 2026

- All clips and Exports now show a separate Delete action beside Open editor and Download, per-row selection checkboxes, Select all visible clips, Clear selection and Delete selected with the actual selected count. Search/view changes clear selection; processing projects cannot be selected for deletion. Desktop and mobile styles keep actions inside the viewport.
- Single and batch actions require confirmation. Each request uses the existing guest-protected DELETE clip API. Source videos/projects and unselected clips stay intact; retained exported versions are removed by the existing API. Batches display request progress, actual successful deletions and per-clip errors. Failed selections remain selected for retry; already completed deletions are not rolled back. No user clips were deleted during verification.
- Open editor from a library row now opens that exact clip instead of merely opening its project without selecting the clip.
- Production build and TypeScript checking passed. **21 deletion/privacy backend tests passed in 19.27 seconds** (`artifacts/clip-delete-backend.xml`), covering ownership, all retained clip revisions, source preservation and busy-job protection. The backend implementation was reused without new API changes; the full backend suite was not rerun for this UI-only update.
- **All six targeted Microsoft Edge tests passed in the final clean run (approximately 1.3 minutes)** (`artifacts/clip-delete-browser.json`): real individual deletion, cancellation, multiple selected clips across two projects, ready-only Exports scope, filtered Select all deletion, partial server failure/retry, guest isolation, existing preview/sticker/voice/editor deletion behavior, dashboard navigation and responsive theme. The new tests initially sent fixture uploads before guest initialization completed (401); waiting for the real connected session corrected the setup race. HTTP 500 is injected only to test error handling; successful deletions and rendered media use the real backend.
- Visually reviewed `artifacts/clip-library-desktop.png` and `artifacts/clip-library-mobile.png`; the 390px layout has no horizontal overflow or overlapping actions. Test projects were cleaned up. Frontend and backend health returned HTTP 200, and the independent backend was left running throughout the frontend update so active user processing could continue.


## Automatic generation feedback and processing popup — October 24, 2026

- Generate now locks immediately, reports submission/transcription/rendering states, and presents success, zero-result explanations and retryable errors directly beneath the button. The request latch prevents repeated submissions. Manual clipping remains optional; the empty-state copy no longer tells users it is required. Import results also initialize the inline feedback after opening the editor.
- Zero results distinguish already-covered moments, quality-rule exclusions and insufficient remaining speech. An explicit **Try Explore all suggestions** retries automatically with lower-scoring selection; existing clips and rendered files are preserved. Counts from 1–100 are maxima, not guaranteed output counts. Selection remains grounded transcript heuristics, without a promise of views.
- Hindi combining marks, native Hindi/Urdu sentence boundaries and contextual hook/payoff markers now participate in quality ranking. Regression fixtures verify qualifying native Hindi, Urdu and Roman Urdu excerpts without invented transcript text.
- A dismissible status card appears as soon as a link or generation request is submitted. Import polling exposes actual owned-project stage, transcription progress and ready/total preview counts. Unmeasured stages show an indeterminate bar. The card and its reopen control render through a body portal, keeping them inside the viewport even when their parent panels are animated. Hiding it does not cancel the job. Download stays manual after rendered preview.
- Final production build and TypeScript checking passed. **245 backend tests passed in 180.52 seconds**, including real FFmpeg exports, privacy/ownership and the new zero-result/import-progress cases (`artifacts/generate-popup-backend.xml`). A first run could not access the system pytest temp directory; the final run used a writable isolated workspace test directory.
- **All 15 Microsoft Edge tests passed in the final full run (approximately 2.9 minutes)**, without skipped/flaky/failed cases (`artifacts/generate-popup-browser.json`). The three focused generation/import checks also passed (`artifacts/generate-popup-focused.json`). This includes a genuine external public MP4 download, immediate/hide/show popup behavior, a real queued Whisper speech transcription with automatically rendered playable preview, count-100/error/retry/zero-result recovery, existing-clip preservation and no automatic downloads. A deliberately injected HTTP 500 verifies error handling only; successful media and ASR paths use real processing.
- An earlier browser run was interrupted while checking popup placement. The parent animation's transform was found to affect fixed positioning; the body portal corrected it. Final mobile assertions verify viewport bounds and no horizontal overflow. Visually reviewed: `artifacts/link-processing-popup-mobile.png` and `artifacts/generate-button-mobile.png`. Only the exact public-video fixture left by the interrupted run was cleaned up; user projects were preserved.
- Both local services remain running on loopback. This validation covers the tested local workflows, not every social-platform URL, maximum-size input, production deployment or guaranteed viral quality.


## Separate Hindi and Roman Urdu outputs — October 24, 2026

- Added explicit Hindi (`आप कैसे हैं`) alongside Roman Urdu (`aap kaise hain`) and Original script in generation, imports and transcript controls. Hindi uses a real Hindi audio pass with the separately cached multilingual small model and Arabic-script token suppression, including partial UTF-8 tokens. This is not English translation. Model labels and processing guidance reflect that Hindi can take longer.
- Hindi → Roman → Hindi uses the saved native snapshot without changing word times. Urdu/Roman-only projects queue a new audio pass for Hindi; confirmation explains replacement of edited text and draft invalidation. Clip IDs/ranges stay intact. Generate can select a new distinct batch after this pass; overlapping existing ranges may legitimately leave zero new suggestions. Manual edits still invalidate stale snapshots safely.
- Bundled OFL Noto Sans Devanagari with source/checksum/license records. Both browser controls and actual ASS exports use a compatible Hindi font. Hindi subtitles remain editable and SRT/VTT retain Devanagari.
- **239 backend tests passed** in 152.84 seconds (`artifacts/hindi-backend.xml`), including eight new job/generation, snapshot, script, three-mode recognition and ASS/font checks. **28 targeted checks passed** (`artifacts/hindi-targeted.xml`). An initial fixture expected a duplicate overlapping clip; it was corrected to exercise a distinct available range.
- **Both actual Urdu/Hindi audio → Hindi MP4 pipelines passed** (`artifacts/hindi-real-speech.json`), using public FLEURS samples and cached Whisper small with genuine word timestamps, automatic renders and Devanagari SRT. Both final samples had two aligned segments. Actual preview frames were visually reviewed: `artifacts/hindi-ur-frame.png`, `artifacts/hindi-hi-frame.png`; corresponding MP4s are retained. Recognition still makes word/name errors; this verifies functioning output, not perfect accuracy. Attribution is in `THIRD_PARTY_NOTICES.md`.
- Early base-model Hindi recognition was poor; the Hindi path now uses small. The speech verification initially stopped when a draft appeared before automatic render queuing; it now waits for ready/error export states. The final passing speech run used isolated temporary projects. Production build and TypeScript passed.
- Two focused Edge tests passed (`artifacts/hindi-focused-browser.json`), covering import payloads, Hindi preview, Unicode SRT/VTT, Hindi/Roman round trips and mobile layout. Temporary session tokens in debug diagnostics were redacted. An initial full run stalled taking a screenshot during concurrent processing and was interrupted. The fresh full run passed all 13 Microsoft Edge tests in approximately 2.3 minutes (artifacts/hindi-browser.json). This includes the earlier real upload, private guest, effects, deletion, MP4/WebM, import and responsive workflows. Final frontend HTTP 200 and backend health OK; both services remain running.

## Automatic Roman Urdu subtitles — October 24, 2026

- Added source-language hints (auto/Urdu/Hindi/English), local Urdu/Hindi-to-Latin script conversion, initial Roman Urdu/Balanced UI choices for new work, import option persistence, and conversion controls for existing transcripts. English remains English; no English-to-Urdu translation is claimed. Original ASR text is saved separately; word start/end values stay unchanged. Unaligned text uses the existing phrase fallback rather than fabricated word timings.
- Script changes invalidate changed exports while preserving clip IDs/ranges. Original-script restoration uses the saved snapshot; subsequent manual edits remove it, and restoring then returns an actionable error instead of overwriting edits. Re-transcription recovers source text explicitly. All new endpoints retain guest ownership checks and processing locks.
- **231 backend tests passed** in 90.20 seconds (`artifacts/roman-urdu-backend.xml`), including 11 new conversion, Hindi/English mixing, alignment, restoration/edit safety, processing lock, guest isolation, job integration, validation and language-hint tests. Earlier targeted run: 20 passed (`artifacts/roman-urdu-targeted.xml`). Initial failures included a Hindi punctuation normalization issue (fixed) and a test cookie restoration mistake (corrected).
- **Actual Urdu and Hindi speech pipelines passed** (`artifacts/roman-real-speech.json`): two short public FLEURS audio fixtures, cached Whisper base with explicit language hints, word-aligned Roman captions, automatic real MP4 rendering, audio probing and Latin SRT output. Exported frames were visually inspected: `artifacts/roman-ur-frame.png`, `artifacts/roman-hi-frame.png`; previews are `artifacts/roman-ur-preview.mp4` and `artifacts/roman-hi-preview.mp4`. Isolated test project databases were removed; user projects were not converted by testing.
- Important observed limit: the small base recognizer made word errors on both samples and emitted Urdu-script text even for the Hindi-hinted sample. Both Urdu and Devanagari input scripts are supported by conversion tests; this verifies a working pipeline, not accurate transcription of every word or a translation-quality benchmark. Names, unusual vocabulary and Roman spelling need review. The first Hindi test-split dataset request returned HTTP 500; the public validation sample was used instead. Attribution is in `THIRD_PARTY_NOTICES.md`.
- Production Next.js build and TypeScript passed. **All 12 Microsoft Edge tests passed** in approximately 1.7 minutes (`artifacts/roman-urdu-browser.json`). The added test uses explicitly entered Urdu fixture text (not simulated ASR), generates and plays a real rendered Roman-caption preview, verifies Latin SRT, restores original text and invalidates the old export, reapplies Roman script and checks 1440/768/390px layouts with no horizontal overflow or automatic download. Existing upload/import/privacy/deletion/effects/bulk workflows remain covered. Mobile screenshot reviewed: `artifacts/roman-urdu-mobile.png`. Final frontend HTTP 200 and API health OK; services left running.

## Public brand and reference UI/UX — October 23, 2026

- Public branding changed to **ZyntraCut AI** after the user rejected the earlier proposed name. This is a proposed name, not trademark/domain clearance. Existing directory, API, ownership, storage and guest-session identifiers are preserved.
- Added working platform shortcuts and shared upload picker, five caption/framing preset cards, synchronized clip-count and engagement sliders, and import aspect-ratio selection. Presets submit actual caption animation, font, style and framing settings. The desktop editor places the rendered preview/timeline beside focused tool panels; mobile keeps a stacked layout. All tools retains the complete existing controls.
- Production Next.js build and TypeScript passed. **All 11 Microsoft Edge tests passed** in approximately 1.5 minutes (`artifacts/reference-ux-browser.json`), including real upload/render/playback/download, guest privacy, deletion, imports and error recovery. This UI-only update did not rerun or modify the backend: the earlier 220-test backend and real-speech results below remain separately dated evidence.
- New checks cover preset values, synchronized sliders, platform input focus, the actual upload file chooser, editor tool switching, reduced-motion support and widths 1440/1024/768/390 without document overflow. Screenshot review caught the sticky preview overlapping later cards; it was corrected and a non-overlap assertion added before the passing run. An exact-label test lookup was also corrected to the accessible combobox role.
- Two targeted Edge checks also passed after strengthening the preset submission assertions (`artifacts/reference-preset-submit.json`): five platform URLs retain the selected style/font/aspect/animation in their API requests, and the responsive/theme workflow still passes. These five requests deliberately exercise a handled import rejection; the separate suite case covers a real public MP4 import, not successful downloads from every platform.
- Review screenshots: `artifacts/reference-ui-1440.png`, `artifacts/reference-ui-390.png`, `artifacts/reference-editor-desktop.png`. The layout follows the supplied reference's visual direction with original code-native artwork and actual user-media cards; it does not add fabricated demo projects or progress. Advanced engine limitations in `PREMIUM_UPGRADE.md` remain applicable.

## Completed pending preview/sticker/voice workflow — October 23, 2026

- **220 backend tests passed** in 164.89 seconds (`artifacts/final-workflow-backend.xml`). New actual-export coverage checks all five sticker schedules across four animation choices, output-time/speed handling, visible and absent sticker pixels, six measured Deep/High strength combinations, source subtitle-stream exclusion, black-band source covering and replacement captions, safe arguments and automatic new-batch preview rendering while retaining existing manual drafts. Earlier media/privacy/import/alignment regressions remain included.
- **11 Edge tests passed** in approximately 1.4 minutes (`artifacts/final-workflow-browser.json`). The new workflow clicks Generate with automatic rendering enabled, sees a playable rendered preview without manual clip creation, exercises seven caption/motion presets, voice controls, sticker schedule/animation controls and source-caption covering, plays processed audio, verifies zero automatic downloads, and checks clip-delete cancellation/confirmation and source preservation. Four widths (1440/1024/768/390), no document overflow, no nested buttons and unique DOM IDs are checked. Existing guide/navigation/private guest, bulk editing, real MP4/WebM downloads, imports, error recovery and theme tests also pass. Initial failures were test locator ambiguities between generated/individual frame fields and the clip-count helper label; the corrected final suite passed.
- **Cached real-speech API pipeline passed** (`artifacts/final-real-speech.json`): actual Whisper base transcription with word timings, automatic captioned MP4 preview, then explicit re-transcription preserving clip IDs/ranges, resetting exports to drafts and producing no extra clips. It ran only after verifying no active user jobs. Temporary test projects were cleaned; real user projects were not deleted or restyled.
- Production build/TypeScript passed; frontend HTTP 200 and backend health checked. Both app services remain running. Reference-inspired charcoal/lime/violet styling remains; the new controls use the same system. Screenshot evidence: `artifacts/final-editor-mobile.png` plus `artifacts/studio-theme-1440.png`/`studio-theme-390.png`.
- Scope and limitations are recorded in `FINAL_AUDIT.md`: separate subtitle streams are excluded, burned-in captions are covered rather than reconstructed, voice filters alter pitch/tone rather than identity, and platform restrictions/ASR accuracy still vary. Testing covers the documented workflows and fixtures, not every possible device/content/combination. Advanced tracking/music/GPU roadmap features remain separate from this completed pending feature set.

## Reference-inspired studio theme — October 23, 2026

- Implemented charcoal surfaces, lime primary actions, restrained violet accents/glow, local Poppins typography, refined inputs/navigation, collapsible sidebar, a code-native caption hero, compact settings grids and actual source thumbnails on clip cards. Existing upload/import, private projects, editing and rendering APIs are unchanged. Attached design notes were treated as reference context for the user's theme request, not as authorization for unrelated product features.
- **10 Edge tests passed** in approximately 1.3 minutes (`artifacts/studio-theme-browser.json`), including the existing real render/download/privacy/delete workflows and a new theme check at 1440/1024/768/390px. Sidebar collapse/expand works; reduced-motion preferences disable entrance animations. An initial run found a legacy flex-basis/wrap conflict causing mobile overflow; that layout was corrected before the passing run.
- Production build and TypeScript passed. Frontend HTTP 200 and backend health OK. Desktop and mobile screenshots were visually inspected: `artifacts/studio-theme-1440.png`, `artifacts/studio-theme-390.png`. No demo projects, invented progress, fabricated performance metrics or nonfunctional navigation entries were introduced. Backend services and user video jobs were not restarted for styling changes.

## Premium caption/editing first stage — October 23, 2026

- Production build and TypeScript passed. **170 existing backend regressions passed** in 76.38 seconds (`artifacts/premium-backend.xml`); **17 new caption/render/alignment/launch-recovery tests passed** in 7.60 seconds (`artifacts/premium-render-tests.xml`). Actual encoded video tests cover both word playback modes across five animation choices, speed-adjusted ASS timing, visible pixels in the safe zone, rhythmic zoom with leveling/denoise, default source-preserving settings, explicit sticker permission and preservation/invalidation of edited word alignment.
- Cached real speech and the local Whisper base model passed the API → word timestamps → actual karaoke MP4 path (`artifacts/premium-real-speech.json`, `artifacts/verified-speech-clip.mp4`). The exported frame `artifacts/premium-caption-frame.png` was visually inspected: readable Poppins captions, highlighted active word, high-contrast outline and no sticker. This is a test fixture, not a product demo result or guarantee of subjective editing quality.
- **9 Edge tests passed** on the final backend in approximately 1.1 minutes (`artifacts/premium-browser.json`), including caption/filter/sticker editing, batch renders, private guests, deletion, real MP4/WebM playback/downloads, imports and timeline-containing mobile editor. The first run caught a transient Windows CreateProcess permission error launching FFmpeg during a batch. Bounded retries for failed starts only were added and tested; permanent permission denial and encoding errors still fail visibly. The rerun passed.
- Frontend HTTP 200 and backend health checked. Both services remain running locally. Original/native High preserves source pixel dimensions for uploads; link downloads still use the chosen 480/720/1080 download limit. Re-encoding with baked-in captions/effects is lossy. Old files require re-rendering to change already baked-in stickers.
- This is an implemented stage, **not the full requested engine**. See `PREMIUM_UPGRADE.md` for unfinished tracking/diarization, multimodal ranking, silence/scene editing, music/SFX, emoji, GPU and durable-job work. Rhythmic zoom is not AI tracking, phrase fallback is not word alignment, and the timeline is a single-video/caption editor rather than a multitrack compositor. Word timestamps can increase CPU transcription time. No claims of millions of views or guaranteed premium editorial quality are made.

## Quality-first selection, readable captions and preview control — October 22, 2026

- **170 backend tests passed** in 63.80 seconds (`artifacts/quality-preview-backend.xml`). Existing actual FFmpeg/PyAV tests cover caption designs/fonts, Warm/Vintage and other filters, fit/crop positions, ratios, webcam cover, speed/audio, MP4/WebM, uploads, ownership and deletion. New selection tests cover weak-content rejection, grounded opening/payoff evidence, sentence boundaries, adjustable thresholds, temporal and content duplication, existing clip preservation and clearing stale evidence after a range edit. Caption phrase tests preserve words and cue bounds.
- **9 Microsoft Edge tests passed** in 57.4 seconds (`artifacts/quality-preview-browser.json`) against the final production build. A real local-video fixture with explicitly entered test transcript exercises default Quality first, zero results at a strict threshold, qualified results at 70, score evidence, actual rendered playback and exactly zero downloads until the user clicks Download. It also verifies caption/filter/framing controls stay disabled while an actual server render request completes, a later draft range seeks to its start, and mobile layout remains within the viewport. The other eight workflows cover private guest isolation, real upload/render/download, caption/filter/sticker edits, bulk exports, MP4/WebM and public-link import. An initial new-test run lacked guest-session bootstrap; explicit bootstrap fixed that test setup.
- Production build and TypeScript passed. Local frontend returns HTTP 200; backend health is OK. Both services remain running. User projects were kept, with no automatic restyling or regeneration of their clips.
- Quality-first scores use deterministic transcript evidence, not an LLM, audiovisual comprehension or validated viral probability. English/Roman Urdu marker coverage is limited. Test fixtures demonstrate behavior and grounding, not real-world retention or millions of views. Candidate count is a maximum, and zero is a valid outcome. Explore all retains the old count-driven suggestions.
- Fixed long subtitle blocks by rendering shorter phrases. Intra-segment phrase timing is estimated from text length, not word-level ASR alignment; SRT/VTT retain edited segment timings. Fixed editing controls that previously remained usable during rendering, guarded against out-of-order dashboard refreshes, and distinguished original source-range previews from previews containing rendered effects. Rendering writes a local-server preview; downloading to the browser is a separate explicit action.

## Multi-platform link studio — October 22, 2026

- Renamed the dedicated sidebar studio to **Link to clips**. It accepts public video URLs through `source_kind:any` without a YouTube-only client restriction; Overview retains the same shared importer. English/Roman Urdu instructions now describe supported platform and direct video URLs.
- **25 importer backend tests passed** in 16.85 seconds (`artifacts/platform-link-import-backend.xml`): real download fixtures, import job/default handling, private-network/redirect rejection and existing compatibility behavior. The older API's explicitly requested `source_kind:youtube` restriction remains for backwards compatibility; the studio never requests it.
- **5 targeted Edge tests passed** in 36.1 seconds (`artifacts/platform-link-studio-browser.json`). Actual public MP4 download through the sidebar opens a playable editor. YouTube/TikTok/Instagram/Facebook/direct-URL form submissions are checked with a deliberately rejected import response; these submission checks do not claim successful downloads from all those platforms. Mobile navigation, bilingual help, stale-job recovery and private-link errors also passed.
- Production build/TypeScript passed; frontend HTTP 200 and backend health checked. Frontend reloaded and left running; backend video jobs were not restarted. Advanced semantic/multimodal ranking, tracking and animated captions remain roadmap items in `UPGRADE_PLAN.md`, not features of this link change.

## Custom text on all clips and call-to-action stickers — October 22, 2026

- **162 backend tests passed** in 82.37 seconds (`artifacts/stickers-all-clips-backend.xml`). Actual decoded FFmpeg exports verify Subscribe/Follow/Like badges in all four supported corners, without transcript subtitles, through the last frame at 2x speed. Bulk settings tests verify explicit inclusion of ready clips, custom text propagation and stale export invalidation; drafts-only behavior remains covered.
- **8 Microsoft Edge tests passed** in 51.8 seconds (`artifacts/stickers-all-clips-browser.json`). The editor test updates custom text and Subscribe sticker settings across two previously ready clips, waits for fresh exports, verifies every clip's saved settings, and continues through real MP4/WebM playback/downloads and deletion. Two earlier browser runs exposed test synchronization errors; the final run explicitly waits for both background export completion and the editor's ready state before further edits.
- Production build and TypeScript passed. API health and frontend HTTP 200 checked; both services are running locally. Real user projects were not restyled or re-rendered by this update.
- **Apply & render all clips** copies every selected effect setting, including format/speed/voice, while preserving each clip's title and time range. Badges are static text stickers, one per clip; image uploads, multiple simultaneous stickers and animated stickers are not implemented. Transcript text still uses saved cue timestamps, separately from the full-duration custom message.

## Fonts, actual filter application and YouTube studio — October 22, 2026

- **158 backend tests passed** in 53.30 seconds. New checks verify that libass selects each of the eight bundled font families rather than silently falling back, and repeatedly save/render/download the same clip with original/Warm/Vintage settings. Decoded downloaded frames verify a real warm color shift and Vintage corner darkening; export versions change and private/no-store responses remain enforced. Dedicated YouTube domain validation and all earlier effects, formats, speeds, guest ownership/deletion and import checks passed. Evidence: `artifacts/fonts-filters-youtube-backend.xml`.
- **All 8 Microsoft Edge tests passed** in 52.4 seconds, with no skipped/flaky/failed cases. New coverage includes locally loaded Poppins font data, font-gallery selection, one-click Apply & render on an existing export, persisted Vintage/Anton settings, a changed preview version, the separate YouTube studio, custom count/font import payloads, wrong-site rejection and handled server errors. Guest isolation, actual uploads/public MP4 imports, MP4/WebM playback/downloads, deletion and mobile layout still passed. Evidence: `artifacts/fonts-filters-youtube-browser.json`.
- **Production build and TypeScript passed.** New fonts are local TTFs with original OFL licenses and recorded source/checksums in `public/fonts/`. Eight new families plus three existing system fonts give 11 choices in the editor and link importer.
- **Live YouTube metadata extraction passed** for the user's supplied URL: duration 1,205 seconds, extractor Youtube, 182 available formats. Evidence: `artifacts/youtube-extraction-followup.json`. The earlier full download/transcription/export of that URL remains recorded below. This follow-up did not redownload/reprocess the entire source. The dedicated-view browser test handles a simulated error to inspect its outgoing options; it does not pretend to generate clips from a mocked successful response. A real external MP4 import exercises the shared import path.

The original Warm filter adjusted only shadows and left neutral/mid-gray pixels unchanged. Warm/Cool now include midtones; Vintage adds explicit sepia coloring. The new Apply & render action saves changes and queues a real rerender, avoiding confusion between a selected setting and an existing ready export. Existing user projects/exports were preserved; no active user job was interrupted during reload. Public-site authentication, bot, regional and DRM restrictions still apply.

## Custom counts and Fast transcription follow-up — October 22, 2026

- Added an explicit Custom button, focused number entry and examples for any integer 1–100. Existing presets remain shortcuts, and controls explain that full-source transcription happens once and is reused for later clip counts. New projects select Fast by default.
- Fast mode now uses a fresh faster-whisper batched wrapper per job, tiny INT8, batch size 4, greedy decoding, VAD and real timestamps. Balanced/Accurate keep the former sequential decoding context. `CLIPFORGE_FAST_BATCH_SIZE` accepts 1–8; larger batches can use more RAM and Fast decoding can change accuracy/context.
- **17 targeted backend tests passed** in 18.94 seconds: batch limits/decoding settings, actual upload/render API regression, custom counts 7/12/30/100, invalid counts, source/clip boundaries, subtitle editing and bulk styling. Evidence: `artifacts/transcription-count-tests.xml`.
- **Updated Microsoft Edge editor test passed** in 31.2 seconds, including Custom focusing the field, submitting 7 to the API, truthful fewer-clips feedback on a short source, styling, real MP4/WebM playback/downloads, clip/project deletion and mobile layout. Evidence: `artifacts/custom-count-browser-results.json`.
- **Real batched Fast Whisper → private guest API → highlights → captioned MP4 pipeline passed** using cached speech/model data. Evidence: `artifacts/batched-fast-speech-test.json`. Production build and TypeScript passed; the updated API/frontend are running locally.

The user's ongoing approximately 20-minute transcription was preserved and completed with 380 saved segments and 5 clips. A subsequent approximately 8.5-minute transcription also finished before the backend was reloaded. No ongoing user transcription was cancelled for the update. CPU-heavy speech testing was deferred until user processing was idle. No universal speedup is claimed; clip count does not limit the first source transcription. Performance comparisons are separate from the functional pass results above.

Completed performance comparison: the same first **60 seconds of a real local source**, tiny INT8 CPU, one warmed-up measurement per path: previous sequential Fast **35.926 s**, batched Fast **4.977 s** (7.22× measured ratio). Evidence: `artifacts/speech-benchmark.json`. Audio decoding and model loading were excluded from both timed sections. This is one excerpt on this machine, not a whole-video, equal-accuracy or universal speed guarantee; Fast's context/fallback/VAD changes can change transcript accuracy and use more RAM. Earlier interrupted or failed benchmark attempts were not counted. No transcript text was saved in the performance report.

## Private guest workspaces and deletion — October 22, 2026

- **130 backend tests passed** in 52.92 seconds. Every project read/mutation, source/poster/export access (including ranges), subtitle download and import-job lookup was checked across separate guest sessions. Tests also cover missing/tampered/expired credentials, cookie flags, hashed token storage, forged owner headers, CSRF checks, real imported-video ownership, and one-time legacy migration. Evidence: `artifacts/guest-privacy-backend-junit.xml`.
- **All 7 Microsoft Edge tests passed** in the final clean run (38.0 seconds), with no skipped/flaky/failed cases. Separate browser contexts received isolated workspaces without login; the owner retained access after reload, while the other guest could not list/open/download/delete its project. The complete upload/edit/style/render/play/download flow passed, including confirmed clip deletion, retained source access, confirmed project deletion and subsequent 404 responses. English/Roman Urdu help, mobile layout, inaccessible old-import recovery, errors and actual public-link imports also passed. Evidence: `artifacts/guest-privacy-browser-results.json`.
- **Real Fast Whisper → highlight → subtitled MP4 export passed** using a guest session and cached real speech/model data. Evidence: `artifacts/guest-private-speech-test.json`.
- **Production build and TypeScript passed** after fixing a delete-section layout overlap discovered by the browser tests. Only the final successful browser run is counted above.

Credentials are random 256-bit opaque HttpOnly/SameSite Strict cookies; only their hashes are stored server-side. Guest sessions expire 180 days after their latest bootstrap/renewal. Authorization is a global FastAPI dependency covering project IDs/import job IDs; upload/import ownership and background-task inheritance are explicit. API responses are private/no-store. HTTPS hosting must configure Secure cookies and exact allowed origins.

Delete this clip removes all of its retained MP4/WebM/ASS revisions, keeping the source and sibling clips. Delete project removes the complete folder and linked import metadata. Busy jobs block deletion. Actual file cleanup and sibling/source preservation were verified; generated browser fixtures were cleaned and user media preserved.

Previously shared projects are preserved and hidden until the local owner uses the one-time key in `data/legacy-workspace-key.txt` through Setup & workflow's restore panel. They are never assigned automatically to the first visitor. Tests verified invalid-key rejection, owner-only access after claiming, removal of the key file and rejection of key reuse.

Limits: a shared browser/profile shares its guest workspace. Clearing cookies, private-session closure, browser/device changes or expiry loses access; normal guest workspaces do not yet have recovery across devices. This access control does not encrypt media from the server operator. Public HTTPS hosting/proxy integration, quotas, rate limiting, retention and production security/load verification remain deployment work. No deployment was performed.

## Speed, caption designs and bilingual guide — October 22, 2026

- **109 backend tests passed** in 67.52 seconds. Added actual 1x, 1.2x, 1.25x, 1.5x, 1.75x, 2x, 2.5x, 3x, 3.5x and 4x exports with duration, audio pitch, video timestamps and subtitle/overlay timing checks. Also checked voice effects with accelerated WebM, invalid speed inputs, clip SRT/VTT timing, unchanged full-source subtitle timing, and six new libass designs against decoded uncaptioned frames. All earlier webcam/framing/import/editor backend tests remain included. Evidence: `artifacts/speed-caption-backend-junit.xml`.
- **All 5 Microsoft Edge tests passed** in 44.3 seconds, with no skipped, flaky or failed tests. Added English/Roman Urdu guide switching, remembered language after reload, six guide steps, all new caption choices, saved/bulk-applied 1.2x settings, an actual 2.5-second MP4 from 3 seconds of source, an actual approximately 0.75-second 4x WebM, and the import speed payload. Real uploads, previews, downloads, public-link importing, errors and mobile overflow checks passed. Evidence: `artifacts/speed-caption-browser-results.json`.
- **Production build and TypeScript passed**. Final frontend returned HTTP 200 and API health was `ok` with FFmpeg available.
- Fixed subtitle rounding at half-centisecond boundaries and added per-export version URLs so rerendering the same clip does not reuse an older cached preview/download.
- Added a six-step user guide in Overview and Setup & workflow, in English and Roman Urdu. Replaced the inaccurate “Private by design” header with “Local workspace”.

Speed controls affect the exported video, audio and caption timing; source start/end values remain source seconds. Six new static caption presets are Electric cyan, Orange label, Red banner, Comic outline, Elegant italic and Heavy shadow. No animated word alignment or custom font uploads are claimed.

Deployment remains deferred for personal local testing, as requested. This application still has a shared workspace with no authentication or per-user ownership; public visitors would not have isolated private data. Neither login accounts nor secure guest isolation was implemented by this update. Vercel frontend integration, persistent worker/storage/database setup and ownership checks remain deployment work. No deployment was performed.

## Webcam hiding and framing follow-up — October 22, 2026

The user clarified that the creator's embedded webcam should be hidden. Added an optional solid-black source-region cover with corner presets, adjustable percentage coordinates/size, source video preview, and batch application. It is applied before reframing and mirroring. It does not reconstruct obscured footage or track moving faces. Also added full-source fitting with padding (new default) and adjustable fixed cropping. Existing exports are preserved until the user saves settings and renders again.

- **84 backend tests passed** in 27.48 seconds, including decoded-frame checks that the selected webcam region disappears in all five ratios, cropping and mirroring; full-source edge preservation; manual crop positions; and invalid bounds. Evidence: `artifacts/framing-backend-junit.xml`.
- **Production build and TypeScript passed** on the final code.
- **The updated Microsoft Edge upload/editor/export test passed** in 19.8 seconds. Verified webcam enable/presets/sliders, actual source-preview frame loading, settings persistence through bulk application, and actual MP4/WebM rendering/playback/downloads. Mobile layout was checked with webcam controls open. Evidence: `artifacts/webcam-browser-results.json`, `artifacts/editor-desktop.png`, `artifacts/editor-mobile.png`.
- The earlier full five-test browser suite and all speech modes are recorded below; only the changed editor workflow was rerun for this follow-up. User project media was not modified for these tests.

## Earlier complete verification — October 22, 2026

This fresh run supersedes the earlier test counts below. All commands completed successfully after restarting the application; interrupted runs were not counted.

- **58 backend tests passed** in 25.87 seconds. Evidence: `artifacts/backend-junit.xml`.
- **Production Next.js build and TypeScript checks passed.**
- **5 Microsoft Edge browser tests passed**, with no skipped, flaky, or failed cases. Evidence: `artifacts/browser-test-results.json`. These exercised the dashboard/mobile layout, real 12 MiB upload, readable HTTP errors, clip-count controls, subtitles/effects, batch rendering, MP4/WebM playback and downloads, SRT export, quality selection, invalid-link rejection, and a real public MP4-link import.
- **All three real Whisper speech pipelines passed**: Fast, Balanced, and Accurate. Each uploaded actual speech, transcribed it, generated a highlight, and rendered a subtitled MP4. Evidence: `artifacts/whisper-fast-test.json`, `artifacts/whisper-balanced-test.json`, and `artifacts/whisper-accurate-test.json`.
- **20 saved ready exports checked; 0 failed.** Existing outputs were decoded and checked for video/audio and timing. Evidence: `artifacts/saved-export-validation.json`.
- Final health check: frontend HTTP 200; API status `ok`; FFmpeg available. Application running at `http://127.0.0.1:3000`.

One older project (`d00a7a19c2c347609a7a3945ce2da4e5`) retains its historical “Processing was interrupted” error. Its source and drafts were preserved; retry transcription/generation from the editor to resume it. This was not a failure in the fresh test run. An intentional unrendered draft in another project was also preserved.

Limits: real TikTok/Instagram links were not tested; private/login-restricted or platform-blocked links are not guaranteed. Maximum-size uploads, four-hour processing, GPU processing, production/load testing, and physical crash recovery remain unverified. The saved exports from the long user video were checked; the entire 101-minute source was not reprocessed in this run.

## Public video links — October 22, 2026

Quality-selector follow-up: link imports now expose 480p/720p/1080p options. The selected value is saved as the project's default render quality and passed to yt-dlp as the preferred source height. Fifty-one targeted import/effect checks passed, including all three quality paths and real 480p/720p/1080p rendering. The import suite now has sixteen cases; the earlier complete-suite count below records validation before this follow-up.

- The user's actual YouTube URL (`https://youtu.be/w3tnaCFW_SE`) was extracted and downloaded, including merged audio/video. The 1,205-second source was transcribed using Fast mode and produced five automatically rendered clips with Dark box captions. Source/project/exports were retained in the app. These clips were real outputs, not test mocks.
- A public W3Schools MP4 link downloaded and probed successfully. The Google-hosted sample URL tried during development returned HTTP 403; the importer reported that failure without pretending the import succeeded.
- Fourteen import-specific tests passed: a real local HTTP-served video download through yt-dlp, background import persistence, source probing, caption-default retention, error reporting/cleanup, unsupported inputs, private-address rejection, mixed public/private DNS, and blocked private redirects. The fixture server is explicitly allowed only inside tests; production rejects it.
- The complete final backend suite passed **56 tests**. Production build and TypeScript checking also passed.
- Five expanded Microsoft Edge browser tests passed, including real external MP4-link import into a playable editor, caption selection, clip-count options, invalid-link feedback, upload, subtitle editing, styling, batch rendering, MP4/WebM playback/download, SRT export and mobile layout.
- TikTok and Instagram extractors are included through yt-dlp, but no actual TikTok/Instagram sample or authenticated account was supplied for a live download test. Public-link support is subject to each platform's current restrictions; every social platform/link is not guaranteed.
- Review the actual source and clip metadata in `artifacts/verified-link-import.json` after running `python -m scripts.verify_import_job <job-id>`. Additional external checks: `python -m scripts.verify_link <url>` and `python -m scripts.verify_link <url> --download`.

## Core editor and effects

Tested on Windows with Node 22.19.0, Python 3.13.3, Next.js 16.4.2, CPU Whisper tiny/base, Microsoft Edge, and the bundled imageio-ffmpeg binary.

- Production Next.js build and strict TypeScript checking passed.
- Six backend tests passed: real upload, video probing, thumbnail, timed subtitle editing, batch FFmpeg/libass rendering of two MP4s, vertical resolution, duration, audio, byte-range retrieval, MP4 download, invalidation after subtitle edits, deletion, invalid inputs, origin checks, and grounded non-overlapping highlights. Requested counts of 30 and 100 produce that many suggestions when transcript material is sufficient, preserve existing clips, and report the actual smaller count on short videos. Counts outside 1–100 and non-integer counts are rejected.
- Three headless browser tests passed: dashboard navigation, setup dialog, mobile layout without horizontal overflow, a 12 MiB video upload through Next.js, manual subtitles, 30/100 clip presets, rejection of a count above 100, actual highlight generation using the selected count, navigation to the generated clips, short-video reporting, batch MP4 rendering with a ready counter, HTML video metadata loading, MP4 download, and readable errors/retry after a plain-text HTTP 500 response. Both installed Edge and Playwright Chromium were used during verification.
- Real Whisper base inference passed on OpenAI Whisper's public JFK speech fixture. No mock transcription was used.
- The expanded backend suite passed 42 tests. These include real FFmpeg exports for all voice presets (original, deep, high, radio, echo, mute), all visual presets (original, vivid, warm, cool, monochrome, vintage, mirror), six subtitle styles plus disabled subtitles, all five aspect ratios, 480p/720p/1080p, H.264/AAC MP4, and VP9/Opus WebM. Pitch was verified by FFT (440 Hz source → about 352 Hz deep / 550 Hz high); visual filters were checked against decoded baseline frames. Silent footage, literal custom text, subtitle fonts/color/position/uppercase, bulk styling persistence, ready-export preservation, SRT/VTT timing/downloads, and invalid settings were also checked.
- Three expanded browser tests passed in Microsoft Edge. They cover selecting a speed mode, voice/video effects, custom text, subtitle style/font, portrait format, bulk styling, actual MP4 and WebM playback, both video downloads, saved SRT downloads, and mobile editor layout without horizontal overflow. Browser fixture projects were deleted; user uploads were retained.
- All three transcription modes passed the real-speech API → highlight → subtitled MP4 test: Fast (tiny, beam 1), Balanced (base, beam 1), and Accurate (base, beam 5). Both models are cached for normal app use.
- A real render benchmark recorded 3.706 s for the former 720p path and 2.243 s for Fast 480p on a 12-second 640×360 test clip. Fast uses a lower resolution and faster encoder settings; this is not an equal-quality comparison or a general speed guarantee. Full results: `artifacts/render-benchmark.json`.
- The real-speech API pipeline passed: uploaded a video containing the speech fixture, submitted transcription through the job queue with a requested count of 30, checked the recognized text, reported one available highlight from the short source, rendered a subtitled vertical MP4, and deleted the temporary project.

Review artifacts are in `artifacts/dashboard-desktop.png`, `artifacts/dashboard-mobile.png`, `artifacts/editor-desktop.png`, and `artifacts/verified-speech-clip.mp4`. Generated fixtures are test material, not user projects. Browser fixture projects are deleted after testing. The cached model is retained for normal use.

Not verified: maximum-size 2 GB uploads, end-to-end processing of the user's entire 101-minute upload, four-hour processing, every supported language and codec, GPU inference, load testing, production hosting, and recovery from an actual mid-render machine crash. No GPU acceleration is enabled. See README for implementation limits. The current version is a local single-user studio; highlight relevance scoring is heuristic, cropping is centered, and subtitles are segment based. Edge affects the browser UI; FFmpeg/Whisper processing speed depends on the backend machine.

Upload regression fixed: Next.js's default 10 MiB proxy body buffer truncated larger video uploads and returned plain-text HTTP 500 errors. The proxy limit now covers the 2 GiB API file limit plus multipart overhead; its timeout allows long uploads. Upload and other API responses handle non-JSON failures without exposing JSON parser errors. The browser upload fixture includes a valid MP4 free-space box to cross the original truncation threshold.
