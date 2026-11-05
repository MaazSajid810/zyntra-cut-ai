> Historical document before the frontend/backend split. Use the [current README](../../README.md) for folder paths and setup commands.

# Existing engine and proposed advanced upgrades

The attached master prompt describes a larger roadmap. This document distinguishes the working application from future work; no score below is a prediction of virality.

Implemented first ranking upgrade: `backend/selection.py` now provides optional thresholded quality selection (the new default), source-aligned candidate boundaries, transcript hook/payoff/completeness/pacing factors, overlap and near-duplicate rejection, ranked results and per-clip evidence. The older algorithm remains under Explore all. This is still deterministic transcript analysis; local semantic models, audio/visual evidence and validated audience analytics below remain future work. Preview rendering and manual download are separate actions, and long captions now render as shorter phrases with estimated intra-segment timing.

## Existing architecture

- Next.js/TypeScript dashboard and editor, Tailwind/CSS, FastAPI backend, SQLite JSON project store, private cookie-based guest workspaces.
- Uploads and background public-link imports use the same stored source and processing pipeline. yt-dlp selects an extractor for the URL; public-network checks also cover redirects and media requests. Link to clips now submits any supported public platform URL rather than restricting the dedicated studio to YouTube.
- `backend/speech.py` uses faster-whisper CPU INT8, cached models and batched Fast transcription. `backend/main.py` orchestrates import, transcription, transcript-derived highlight candidates and render queues. Inspect its `highlights` and processing functions for ranking work.
- `backend/media.py` uses FFmpeg, PyAV probing, ASS subtitles/fonts, voice/color filters, source-relative webcam covers, adjustable fixed reframing, speed and export quality. The editor supports custom text, static call-to-action badges, transcript editing and batch exports.
- Highlights currently use transcript heuristics and existing timestamps. They are not multimodal understanding, emotion detection or validated viral probabilities. Captions are segment based; framing is fixed rather than active-speaker tracking.
- CPU transcription and encoding, source duration/resolution, first model downloads and platform download restrictions affect latency. Browser choice does not accelerate server-side inference. Two render workers limit resource contention; jobs are not a durable distributed queue.
- Existing API groups cover guest/session ownership, project upload/list/delete, transcript save/subtitle download, highlight generation, clip CRUD/bulk settings, individual/batch rendering, source/export/poster delivery, and link import/status.

## Incremental implementation order

1. Complete multi-platform link studio and verify real downloads through the shared importer. Keep unsupported/private/blocked links as actionable errors with upload fallback. Do not claim every URL can be downloaded.
2. Add a versioned candidate analysis schema with measured factor evidence, adjustable thresholds, deduplication and explicit missing signals. Preserve saved manual clips and exports; never manufacture timestamps or dialogue. Add fixtures covering complete/incomplete stories, overlapping candidates and too few qualified results.
3. Add bounded audio-energy/silence and scene-change measurements, then optional local semantic analysis with model availability/status and a truthful fallback. Benchmark real content before selecting new model dependencies; no new model is installed by this link update.
4. Add actual word timestamps and speed-adjusted animated caption rendering, then test synchronization and transcript-edit invalidation. Word-level animation must not be advertised before verified.
5. Add opt-in face/speaker tracking and smooth reframing with gaming layouts, respecting the existing user preference to hide webcam areas. Validate on multi-speaker, no-face and moving-face samples.
6. Add nondestructive editing decisions for silence/fillers/zooms and hook suggestions from source footage, including accurate remapped subtitle times. Review contextual meaning before hook-first restructuring.
7. Add configurable content presets and grounded title/description/hashtag/thumbnail suggestions, preserving editorial review and labelling inferred metadata.
8. Add durable jobs, safe pause/resume/cancel/recovery, resource-aware GPU options, cleanup policies and observed performance analytics. These require lifecycle tests and deployment design beyond the current local queues.

Each stage needs appropriate export/ownership regression checks and representative source-video evaluation. The full advanced engine is not implemented by changing link acceptance. No automatic publishing is included.
