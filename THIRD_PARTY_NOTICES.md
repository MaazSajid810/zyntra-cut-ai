# Roman subtitle dependencies and verification fixtures

- **Noto Sans Devanagari**, Noto Project Authors / Google Fonts, SIL Open Font License 1.1. Bundled as `frontend/public/fonts/NotoSansDevanagari.ttf` with `notosansdevanagari-OFL.txt`; source URL and SHA-256 are recorded in `frontend/public/fonts/manifest.json`. Hindi captions use this script-compatible font. The existing Whisper implementation also caches the multilingual `Systran/faster-whisper-small` model for Hindi recognition; no new paid API or external transcription service is used.

- **urdunlp**, hammasbuilds, version 0.2.0, pinned source commit `a2622de9aa14ba508772d9dcd2d8b7073093515c`: [source](https://github.com/hammasbuilds/urdunlp/tree/a2622de9aa14ba508772d9dcd2d8b7073093515c). Code is MIT; bundled statistical/lexicon data is **CC BY-SA 4.0**, derived from Dakshina (Roark et al., LREC 2020), Wikipedia and HotpotQA. Its unchanged dependency distribution carries both licenses. Retain those attributions/licenses when redistributing the dependency/data; modifications to that data must comply with its share-alike terms. [Data license](https://github.com/hammasbuilds/urdunlp/blob/a2622de9aa14ba508772d9dcd2d8b7073093515c/LICENSE-DATA), [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
- **uroman**, Ulf Hermjakob / USC Information Sciences Institute, version 1.3.1.1: [source](https://github.com/isi-nlp/uroman), Apache 2.0. Used for Devanagari Romanization, with local informal spelling normalization in `backend/romanization.py`.
- **FLEURS**, Google, [dataset](https://huggingface.co/datasets/google/fleurs), **CC BY 4.0**. Verification downloads Urdu `ur_pk/test` row 0 and Hindi `hi_in/validation` row 0. Audio, reference metadata and derivative preview clips are retained only as local test artifacts; filenames begin `artifacts/roman-`. Rendered test captions are machine transcriptions/transliterations and may contain errors; they are not the dataset's reference transcript or product demos. See [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

This notice supplements the existing dependencies' individual licenses; it does not relicense unrelated application code.

## October 24 studio and language additions

- **Pillow 12.3.0** normalizes uploaded static logos and measures watermark text. Its distribution carries the HPND/Pillow license.
- **Noto Sans Arabic**, Noto Project Authors / Google Fonts, SIL OFL 1.1. The bundled font and license are `frontend/public/fonts/NotoSansArabic.ttf` and `frontend/public/fonts/notosansarabic-OFL.txt`; source and SHA-256 are recorded in the font manifest. Used for readable Urdu shaping through libass.
- **SentencePiece 0.2.2**, Google, Apache 2.0, tokenizes the local translation model inputs. **CTranslate2**, already installed with faster-whisper, runs the translation models on CPU INT8.
- Local translation uses **Argos/OpenNMT English–Urdu 1.9 and English–Hindi 1.1 packages**, in both directions, listed by [Argos's package index](https://github.com/argosopentech/argospm-index). `scripts/setup_translation.py` installs them once into `data/translations`, retaining each package's metadata and README. The official server returned 403/404 for some packages in this environment; the installer uses immutable Hugging Face mirror revisions with pinned SHA-256 checksums. Each installed package records its download source and hash in `source.json`. Preserve model-specific attribution/licensing from the packages and upstream sources when distributing models; the application's license does not relicense model weights or training data.
- Pop, ding and whoosh audio are synthesized by this application's FFmpeg expressions. No proprietary editing-software sound/sticker assets are included.


Noto Sans Devanagari (Noto Project Authors / Google Fonts) is bundled under SIL OFL 1.1. The license is frontend/public/fonts/notosansdevanagari-OFL.txt; source and SHA-256 are recorded in frontend/public/fonts/manifest.json. Hindi also caches the free multilingual Systran/faster-whisper-small recognition model locally.

## Native-language additions

- Noto Sans Gurmukhi and Noto Sans Bengali, Noto Project Authors / Google Fonts,
  SIL OFL 1.1. Bundled fonts, licenses, official source URLs and SHA-256 checksums
  are recorded under `frontend/public/fonts` and its manifest. Used for native caption
  exports; no competitor assets are included.
- Optional English/Spanish Argos packages use the same local CTranslate2 engine.
  The installer pins immutable mirror revisions and package checksums for these
  downloads, validates metadata/model files and records attribution in each
  private model directory. Model weights are not part of the Git repository.
