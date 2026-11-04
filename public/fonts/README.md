# Bundled subtitle fonts

These unmodified fonts are redistributed from the official Google Fonts repository under their included SIL Open Font License files:

- Anton — `Anton-Regular.ttf`, `anton-OFL.txt`
- Bebas Neue — `BebasNeue-Regular.ttf`, `bebasneue-OFL.txt`
- Poppins — regular and bold TTFs, `poppins-OFL.txt`
- Righteous — `Righteous-Regular.ttf`, `righteous-OFL.txt`
- Bangers — `Bangers-Regular.ttf`, `bangers-OFL.txt`
- Lobster — `Lobster-Regular.ttf`, `lobster-OFL.txt`
- Pacifico — `Pacifico-Regular.ttf`, `pacifico-OFL.txt`
- Kalam — `Kalam-Bold.ttf`, `kalam-OFL.txt`
- Noto Sans Devanagari — Hindi captions, `notosansdevanagari-OFL.txt`
- Noto Sans Arabic — Urdu, Pashto, Sindhi and Arabic-script captions, `notosansarabic-OFL.txt`
- Noto Sans Gurmukhi — Punjabi Gurmukhi captions, `notosansgurmukhi-OFL.txt`
- Noto Sans Bengali — Bengali captions, `notosansbengali-OFL.txt`

`manifest.json` records the exact source URLs and SHA-256 checksums. Source: https://github.com/google/fonts/tree/main/ofl . `python -m scripts.setup_fonts` refreshes the assets from that source; it is not run by the app at startup. These are public font assets, never guest media. Existing Arial/Impact/Georgia options use installed system fonts.
