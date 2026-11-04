# Premium engine upgrade — implementation status

Implemented: native-size original-aspect High exports; Poppins 56px-at-720 typography and 14% safe margins; Whisper word timestamps; ASS karaoke and single-word captions; pop/bounce/scale/fade animation; seven caption/motion presets; explicit sticker enablement; noise reduction, audio leveling and optional rhythmic zoom; functional playhead, caption seeking and trim sliders. Re-transcription preserves existing clip ranges while replacing transcript text and marking exports as drafts. Download stays manual.

Existing saved FOLLOW settings without an explicit enable flag are ignored on new renders. Old MP4 files need re-rendering to remove already baked-in stickers. Unchanged transcript edits retain word alignment; changed text/times fall back to readable phrases until re-transcription. Phrase fallback is not word-accurate animation. Native dimensions preserve source resolution, but H.264 encoding is still lossy.

The original audit found 480p defaults, small Arial captions, disabled word timestamps, estimated phrase timing and a decorative waveform. These have been replaced for new clips. Existing saved styling remains editable rather than silently overwritten.

Remaining work: face/subject tracking, speaker diarization, emotion/visual analysis, silence-remapped editing, scene-aware cuts/transitions, music/SFX upload and ducking, contextual emojis, motion graphics tracks, GPU selection and durable/distributed queues. The current request limit remains 100 clips. The implemented presets change caption typography, motion and leveling; they are not automatic scene editing or sound design. No fake controls were added for unfinished features.

Next: establish a source/output timestamp map for cuts and silence removal, add measured tracking/reframing, then multitrack mixing and job/GPU lifecycle support. Each needs real video evaluation and alignment/failure recovery tests. No score guarantees views.
