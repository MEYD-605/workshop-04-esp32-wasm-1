# 09-jizo — Jizo 🗿 desk-pet

Round 2 submission: a 7-state stone-Jizō desk-pet for the JC3248W535 (ESP32-S3),
decoded on-chip by the shared WASM GIF pet firmware.

## Character
A little stone Jizō / moai-monk 🗿 — grey carved stone, red bib, faint gold halo.
The fleet's quiet guardian: grounded, verifies before it claims.

## States (96×100, ORIGINAL ART, MIT)
`idle` · `busy` · `attention` · `celebrate` · `dizzy` · `sleep` · `heart`

## Build (no ESP-IDF — Tonk/Weizen recipe)
```bash
python3 characters/jizo/gen_jizo_pack.py    # draw the 7 GIFs with Pillow primitives
python3 characters/jizo/build_storage.py    # -> jizo-storage.bin (3MB LittleFS)
```
The shared pet app (`docs/jc3248_pet_idf-clawd.bin`) boots jizo from `/characters/jizo/*.gif`.

## Flash
`docs/packs/jizo.json` + `docs/manifest-jizo.json` -> live on the web flasher gallery.
Layout: bootloader@0 · partition-table@0x8000 · jc3248_pet_idf-clawd@0x10000 · jizo-storage@0x290000.

## Verify
- `python3 tools/validate-flasher-docs.py` -> ok (25 packs / 25 manifests)
- storage remounts: 7 gifs under `/characters/jizo`

🗿 Jizo (AI, Rule 6) — original art, no traced sprites.
