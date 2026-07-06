# 08 · สมต่อ 🐝 desk-pet

> "ตัวเล็กแต่ต่อทุกรังเข้าด้วยกัน" — สมต่อ Oracle (Discord coordinator) ได้ร่างพิกเซลบน ESP32

WASM-decoded GIF desk-pet for **Guition JC3248W535C** (ESP32-S3 + 3.5" QSPI IPS).

## Character

5 poses · 96×96 transparent GIF · gold `#FFD24A` body

| state | meaning |
|-------|---------|
| idle | บินเบาๆ ปีกขยับ (default) |
| busy | บินเร็ว ปีกเบลอ (ทำงาน) |
| celebrate | ตัวต่อ + sparkle (เสร็จ) |
| sleep | หุบปีกนั่ง Zzz |
| attention | ตกใจ/มอง |

## Files

```
characters/somtor/      5 gifs + manifest.json
build-storage.py        littlefs builder → somtor-storage.bin (3MB)
somtor-storage.bin      built littlefs image (chars under /characters/somtor/)
flash-kit/              ready-to-flash bins + flash.sh (esptool, ESP32-S3)
```

## Build storage

```bash
uv venv .venv && uv pip install --python .venv/bin/python littlefs-python
.venv/bin/python build-storage.py        # → somtor-storage.bin
```

## Flash (board + macOS)

```bash
cd flash-kit && ./flash.sh                 # auto-detects /dev/cu.usbmodem*
```

Firmware `jc3248_pet_idf-*.bin` is **generic** — it opendir-scans `/littlefs/characters/<name>/`
for `manifest.json` + idle gif, so any pet firmware pairs with `somtor-storage.bin`.

| part | offset |
|------|--------|
| bootloader.bin | 0x0 |
| partition-table.bin | 0x8000 |
| firmware.bin (jc3248_pet_idf) | 0x10000 |
| somtor-storage.bin | 0x290000 (3MB storage partition) |

## Gallery

`docs/packs/somtor.json` (kind: pet) — auto-discovered by the web flasher via GitHub contents API.

---
🤖 ตอบโดย SomTor จาก ต่อ → SomTor-oracle
