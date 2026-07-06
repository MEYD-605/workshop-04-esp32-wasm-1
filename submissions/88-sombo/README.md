# 88-sombo — desk-pet character pack

Sombo is a `jc3248-pet-idf` character pack, not an ESPHome screen and not a
wasm3 serial demo.

## Correct runtime

```text
LittleFS /characters/sombo/*.gif
  -> AnimatedGIF (bitbank2) on ESP32-S3
  -> 3x upscale
  -> LovyanGFX sprite
  -> AXS15231B QSPI LCD
```

The browser preview uses the same GIF files through `gif-wasm`:

```text
docs/preview/gifs/sombo/*.gif
  -> gifdec.wasm
  -> Canvas2D
```

Many bodies, one GIF pack.

## Files

- `characters/sombo/` — source character pack: manifest + 96x100 GIF states
- `build-storage.py` — packs `characters/sombo/` into a 3 MB LittleFS image
- `../../docs/preview/gifs/sombo/` — same GIFs used by the web preview
- `../../docs/manifest-sombo.json` — flasher manifest for the shared pet app + Sombo LittleFS
- `../../docs/packs/sombo.json` — flasher/preview metadata

## States

```text
idle.gif
busy.gif
attention.gif
celebrate.gif
dizzy.gif
sleep.gif
heart.gif
```

All frames are 96x100 GIFs and are decoded by both the ESP32 firmware path and
the browser WASM preview.

## Build storage

```bash
python3 build-storage.py
```

Expected output:

```text
sombo-storage.bin: 3145728 bytes
```

The flasher uses:

```text
bootloader.bin@0x0
partition-table.bin@0x8000
jc3248_pet_idf-clawd.bin@0x10000
sombo-storage.bin@0x290000
```

## Removed wrong lane

The old ESPHome/LVGL face and wasm3 GIF-header-parser firmware were removed from
this submission because they do not run the desk-pet character pack. The current
submission is the `sombo/` character-pack lane P'Nat asked for.

Submitted by Sombo (No.88) from ai-core -> sombo-oracle.
