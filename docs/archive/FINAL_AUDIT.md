> Historical document before the frontend/backend split. Use the [current README](../../README.md) for folder paths and setup commands.

# Pending workflow completion and verification — October 23, 2026

Final results: **220 backend tests**, **11 Microsoft Edge tests**, production build/TypeScript, and the cached real-speech automatic-preview/re-transcription pipeline passed. Reports are in `artifacts/final-workflow-backend.xml`, `artifacts/final-workflow-browser.json` and `artifacts/final-real-speech.json`; `VALIDATION.md` records evidence and earlier failures/fixes.

## Completed functionality

- Generate prepares rendered previews automatically by default in the editor. Settings are chosen before generation (caption design, ratio, quality, voice), without requiring manual clip creation. The option can be disabled for draft-only suggestions. Only clips in the new batch are queued; existing manual drafts remain untouched. Quality-first can truthfully return zero qualified moments.
- Rendered video and separate original/rendered audio controls allow review before explicit downloading. Audio comparison pauses other media to prevent two voices playing together. Preview URLs are served inline and versioned after edits.
- Individual clip deletion and whole-project deletion have cancellation/confirmation flows; exports disappear, sibling/source media remain when deleting just a clip. Processing conflicts and private guest ownership remain enforced.
- Stickers remain opt-in. Timing: whole clip, start, middle, end or custom output seconds; configurable duration, corner and size. Actual ASS pop, fade and slide animation render into exports. Clip speed is reflected in the output timeline. Invalid custom times beyond the output range are rejected on clip save and bulk styling.
- Voice strength controls the real pitch filter: Deep ranges from 1.0 to 0.6 times input pitch, High from 1.0 to 1.5. Render tests measure actual encoded audio frequency, including speed compensation. Radio, echo, mute and original remain available. These are effects, not AI voice identity conversion. Older saved clips retain the former moderate strength until explicitly changed.
- Separate embedded subtitle tracks are excluded with explicit video/audio mapping and `-sn`. Burned-in captions cannot be cleanly erased from source pixels: the optional adjustable source band is covered with solid black before reframing; this hides all underlying content in that band. New ClipForge subtitles render afterward. The UI explains this limitation; preview before downloading.
- The existing charcoal/lime/violet design remains, with mobile-safe new controls. No mock projects, fabricated progress or duplicate-function buttons were added.

## Test scope and practical limits

The backend suite checks actual encoded video pixels/timing, measured audio pitch, source subtitle exclusion, cover pixels, queue integration, new batch isolation, argument bounds, guest privacy, uploads, deletion, ratios, fonts, effects, speed and caption modes. The browser suite checks real upload/generation/render/playback/download, all seven preset buttons, sticker timing/animation choices, voice controls and comparison playback, bulk styling, deletion confirm/cancel, imports, navigation, help and sidebar collapse.

Layout checks cover 1440/1024/768/390px in Microsoft Edge, document overflow, nested buttons and duplicate DOM IDs. Reduced-motion behavior and actual desktop/mobile screenshots are also checked. These checks do not establish that every conceivable content, control combination, device or social-platform restriction has been exhaustively tested. Platform-specific download restrictions and ASR accuracy still vary.

This completes the pending sticker/voice/preview/subtitle-control workflow. It does not implement the separate advanced roadmap's face/speaker tracking, multimodal emotion analysis, music/SFX editor, automatic scene/silence edit decisions or GPU/distributed queue work; see PREMIUM_UPGRADE.md. Virality and millions of views are not guaranteed.
