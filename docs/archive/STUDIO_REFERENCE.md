> Historical document before the frontend/backend split. Use the [current README](../../README.md) for folder paths and setup commands.

# ZyntraCut AI: editing reference and implementation status

Updated October 26, 2026.

The user supplied CapCut and DaVinci Resolve screenshots and a suggested feature document as inspiration. Keep the existing **ZyntraCut AI** brand. The latest creator-page screenshots supersede the earlier dashboard theme: Create/Explore/Wizard/Studio use an original white/black/blue layout, while the full editor retains dark panels, lime actions and violet accents. These references do not change the application's name, authorize copying their assets, or require replacing the working Next.js/FastAPI application with the attachment's proposed Tauri project.

## Editor direction

The reference suggests a useful editing workspace: media/tools on the left, a central player, selected-item properties on the right, and tracks below. Implement controls against saved editing decisions and the export engine. A waveform must come from actual audio samples. A timeline track must edit actual rendered media. Do not introduce decorative tracks, stock clips presented as user media, or controls for unsupported effects.

The original dark/lime workspace remains at `/workspace`; the new creator platform is the default home. `/editor` opens an owned project directly. See `PLATFORM_UPGRADE.md` for the independent module mapping and the explicit limits of local command/design tools.

## What works in the current application

| Area | Current implementation |
| --- | --- |
| Media | Local video upload, public-link import, source probing, thumbnails, saved projects and private guest ownership |
| Clip editing | Visual drag/keyboard trim and range movement, gesture-based undo/redo, saved source start/end, fixed crop/full-frame fit, five aspect ratios, 1x to 4x playback speed |
| Captions | Real Whisper word timestamps, karaoke/word animation when aligned, editable text/times, phrase fallback after edits, SRT/VTT |
| Subtitle languages | Original, Urdu, Hindi, Roman Urdu and English; local English/Urdu/Hindi translation; source/output choices are independent |
| Timing | Timestamp-normalized audio before ASR, output-speed-aware captions, per-clip caption sync from -5 to +5 output seconds |
| Branding | Opt-in text watermark and uploaded static logo, opacity/size/color controls, pointer dragging, keyboard placement and X/Y sliders |
| Supporting footage | One uploaded B-roll item per clip, full-frame or picture-in-picture, output-time range, looping and optional fade |
| Photos | One uploaded photo layer per clip, PNG/JPEG/WebP normalization, output-time range, draggable/keyboard placement, opacity, full-frame contain/cover, separate logo support |
| Timeline | Actual source-audio waveform, caption seek blocks, draggable/resizable photo and B-roll timing, music coverage and timeline zoom. Changes save through existing clip settings and affect exports. This is a single source range with supporting layers, not arbitrary multi-source editing. |
| Analysis | Cached 2 fps visual changes, half-second audio levels, threshold-based silence intervals, source-speech hook/payoff ranking and duplicate rejection. Auto quantity returns qualified nonoverlapping clips up to 100; short-source minimum duration adapts. These are explainable heuristics, not emotion recognition or view probabilities. |
| Audio | Source voice filters with pitch strength, leveling, denoise, uploaded looping music, volume, timed synthesized pop/ding/whoosh |
| Effects | Existing color filters plus cinematic, sepia, soft, sharpen and blur; rhythmic zoom; black/white entry/exit fades and B-roll dissolve |
| Stickers | Explicitly enabled follow/subscribe/like badges, start/middle/end/custom schedules, pop/fade/slide animation |
| Review/export | Generated previews, manual downloads, MP4/WebM, 480p/720p/1080p, batch render and individual/bulk clip deletion |

These are an original, bounded implementation. They are not complete CapCut Pro feature parity.

## Work still required for a full multi-track editor

- Versioned timeline document with multiple independent video/audio/text items, source in/out, track ordering and output placement.
- Backend validation and an FFmpeg composition plan for arbitrary sequences, rather than the current single source range plus one B-roll overlay.
- Split, merge, ripple delete, snapping, track mute/lock, undo/redo and tested project autosave.
- Low-resolution preview proxies and a real-time compositor. A measured source waveform is now implemented.
- Keyframes, easing, speed curves, arbitrary transform animation and cross-clip transitions.
- LUT/curve/HSL grading, chroma key, background segmentation, face/subject tracking and moving subject reframing.
- Silence/filler edits with correctly remapped audio and caption timestamps; semantic clip analysis beyond the implemented transcript ranking and measured scene/audio signals.
- Durable cancellable jobs, resource limits, optional GPU paths, load tests and Windows desktop packaging if the user later requests a desktop build.

Each stage needs actual exported media and ownership regression checks before its controls become available. Keep the current working application during these additions.

## Verified limits

- October 25 editor regression: production build and TypeScript checking passed; **311 backend tests passed**. All **22 Edge scenarios** passed across full/focused runs: the latest full batch passed 21, and its screenshot-timeout case passed separately in 14.7 seconds. Real timeline trim, layer timing, save/reopen, exports, deletion, privacy and responsive layouts were checked.
- Real Urdu and Hindi speech each passed the automatic Roman Urdu ASR-to-MP4 check after audio normalization. This verifies processing and export, not perfect recognition or spelling.
- Actual English speech produced Urdu, Hindi, Roman Urdu and English MP4/SRT outputs. Translated words do not receive fabricated source-word timing. Translation can change or omit meaning: the JFK sample lost a negative statement, and the app flags that possible omission for review while showing original text. This is not a complete semantic correctness detector.
- Per-clip sync changes both burned-in captions and clip SRT/VTT; whole-project subtitles remain on the original source timeline. Edited/translated phrases may use estimated timing inside their recognized source segment.
- Latest recovery update: both the supplied Instagram reel and the original TikTok short URL imported through the running app, with audio, source previews, posters and playable MP4 range exports (`artifacts/social-recovery-live-api.json`). Earlier connection resets were real; bounded per-request recovery and retaining resolved short-link URLs allowed these samples to complete. Persistent failures and other platform restrictions remain possible. Facebook end-to-end import is not established by these results. No browser cookies or access controls were bypassed.
- 4K export, a freely editable multi-track timeline, GPU processing, arbitrary sticker/GIF libraries, tracking and segmentation are not implemented. Do not advertise them as working.

Evidence: `artifacts/photo-final-backend.xml`, `artifacts/photo-formats-final.xml`, `artifacts/photo-overlay-browser.mp4`, `artifacts/photo-full-browser.mp4`, `artifacts/photo-panel-mobile.png`, `artifacts/studio-browser-export.mp4`, `artifacts/translation-verification.json`, `artifacts/translation-english-urdu.mp4`, and `artifacts/roman-fast-small-auto-real-speech.json`. Latest browser coverage: 22 scenarios passed across full/focused runs (21 in the latest full batch plus a successful targeted rerun). Current evidence also includes `artifacts/editor-release-backend.xml`, `artifacts/visual-timeline-export.mp4` and `artifacts/reference-editor-desktop.png`. Artifact media are verification fixtures, not user projects.
