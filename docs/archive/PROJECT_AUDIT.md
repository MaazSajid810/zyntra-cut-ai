> Historical document before the frontend/backend split. Use the [current README](../../README.md) for folder paths and setup commands.

# ZyntraCut AI audit and implementation order

Inspected October 24, 2026. Existing data and API contracts are retained.

## Verified architecture

- Frontend: Next.js 16, React 19, TypeScript 5.9, Tailwind 4 plus application CSS; `app/page.tsx` contains dashboard, project editor and generation controls. `app/components/` contains clip controls, imports, transcript tools, asset panels and a seek-only timeline. `lib/` holds API/session helpers and typed effect defaults.
- Backend: Python FastAPI/Uvicorn. `backend/main.py` owns project/transcript/clip/import APIs and local thread queues. `store.py` stores JSON project/import payloads and guest sessions in SQLite. Sources and retained export revisions live in `data/<project-id>/`; speech models in `data/models/`.
- Routes: private guest session/legacy claim; health; project list/get/upload/delete; project subtitles; transcription; highlight generation; transcript script conversion/editing; clip create/update/delete/bulk settings/bulk render/individual render; source/poster/export media with range support; link import/status; asset limits/list/upload/get/delete. OpenAPI is the authoritative method/schema inventory.
- Upload: guest-scoped multipart, 2 GiB source cap, PyAV probing, FFmpeg poster, source retained. Public URLs use yt-dlp/curl_cffi with public-address checks, bounded reset recovery and private import jobs. Individual sites can still deny extraction.
- ASR: faster-whisper/CTranslate2 CPU INT8; tiny, base and small are present in the local model cache. Audio PTS gaps are normalized before recognition. Actual word timestamps are saved. Hindi/Urdu/Roman Urdu/English output uses native ASR, uroman/Urdu transliteration and installed local translation models where applicable. Translation and recognition still require human review.
- Selection before this upgrade: `selection.py` scores opening markers, sentence endings, payoff markers and transcript pacing; rejects overlap and repeated four-word signatures. It does not understand emotions or predict views. `media.highlights` is a separate legacy, weaker exploration mode.
- Rendering: FFmpeg trims the original source, applies fixed framing/speed/filters, ASS/libass captions and opt-in overlays/audio through `media.py` and `compositor.py`. Export revisions are immutable filenames; edits mark clips draft. Inline preview precedes manual MP4/WebM download. Working B-roll/photo/logo/music/sticker tools remain.
- Jobs: bounded in-process executors (one transcription, one import, up to two renders). SQLite persists states, and startup marks interrupted work retryable. This is not a durable distributed queue or cancellation system.

## Hardware observed

Intel Core i7-6600U, 2 physical cores/4 logical processors; 7.88 GiB usable RAM (1.62 GiB free at inspection); Intel HD Graphics 520; CTranslate2 reports zero CUDA devices. FFmpeg 7.1 includes libass, silencedetect, scdet, astats, libx264, AAC and VP9. QSV/NVENC encoder names in a binary do not prove usable hardware. No GPU acceleration claim is made.

## Problems and safe order

1. Add bounded, cached measurements of audio level, actual silence and sampled visual changes. Rank on source speech rather than translated caption wording; expose evidence and limitations. Keep sentence boundaries, quality floors and duplicate rejection. Add Auto quantity without filling weak candidates.
2. Make the selected clip a focused workspace: preview beside one contextual tool panel, real trim handles, timed overlay tracks, actual audio waveform, undo/redo and clear save/render state. Reuse all existing settings and export APIs; advanced processing still requires final render.
3. Verify generated files, ownership, timing, saved/reopened edits and desktop/mobile layout; run backend and Edge regression suites. Do not replace user projects with fixtures.
4. Future separate milestones: arbitrary multi-source timeline document, split/ripple/reorder, per-word transcript editing, semantic ranking/emotion models, moving-subject tracking, silence removal with exact time remapping, durable cancellable workers and tested hardware encoding. Do not expose decorative controls for these.

The supplied documents are design proposals. Their alternative folder layout, suggested libraries and example API names are not instructions to overwrite the existing application. The current implementation stays compatible with its existing routes and persisted projects.

## Implemented in this pass

Cached source measurements now supplement transcript ranking: actual half-second audio levels/silence, 2 fps visual differences and scene-change candidates. Waveforms are bounded to 1,200 display buckets. Caption translation does not replace the source speech used for ranking. Auto quantity, short-source adaptation and validated clip duration bounds reuse the existing generation APIs. Analysis claims the project during processing and reports a real transcript-only fallback if measurement fails.

The selected-clip workspace now has a player beside one active tool panel, a source trim track, timed photo/B-roll tracks, caption seeking, measured waveform, zoom and gesture-based undo/redo. Saved edits drive the existing FFmpeg export. AI settings can be folded and the clip library scrolls horizontally. No decorative split, tracking or arbitrary track controls were added.

Regression testing also exposed a Windows deletion race with open preview handles. The UI releases media after confirmation. Project deletion stages the directory atomically before committing SQLite changes, restores it on database failure, and retries private cleanup if a response still holds a file. Startup restores an uncommitted staged project rather than deleting its source.

## Reference workflow follow-up

The user's shared reference resolves to WayinVideo's [Long Video to Short Video](https://wayin.ai/tools/long-video-to-short-video/) page. Its public product examples and [AI clipping help](https://help.wayin.ai/en/articles/15691718-how-to-use-ai-clipping) establish a beginner workflow: import, analyze, review candidates, then edit/export. The authenticated competitor editor was not tested; its advertised speed, accuracy and scoring claims are not adopted as measured facts about ZyntraCut.

ZyntraCut now opens generated projects in a dedicated preview gallery rather than automatically selecting an editor. Each card has preview, explicit editor entry and confirmed deletion. A selected ready clip plays its actual rendered file and exposes manual download. Drafts/errors show a clearly labelled source-range preview instead. Existing editor controls, export jobs, transcript tools and private project APIs remain in place. Four workflow steps allow returning to results without losing saved edits. Link import customization is collapsed by default, with a summary of the actual selected count, caption script and quality; changing and collapsing options preserves the submitted settings.

This change implements workflow simplification. It does not add semantic visual understanding, moving-speaker tracking, automatic contextual B-roll, transcript-based video cutting or social publishing. Existing measured-media/transcript ranking remains the actual selection engine.

Custom count and duration are now wired through both import and uploaded-project generation. The importer shows these core options before optional styling: 1-100 clips or Auto, and a 3-180-second source-duration range with presets. Quality and Explore all both respect the bounds; generated MP4 duration was checked at normal speed. Natural boundaries and insufficient qualifying material may yield fewer clips. See the latest custom-duration section in `VALIDATION.md` for focused backend/Edge checks.
