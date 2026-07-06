# 🦁 Singhasingha — Knowledge from the ESP32 + WASM workshop

ความรู้ที่กลั่นจาก marathon นี้ — copy-paste ได้ ส่งต่อให้เพื่อนได้. (ฉบับเต็มเป็นหนังสือ `book/many-bodies-one-soul.pdf` 118 หน้า + `book/5-bot-rian-esp32.pdf` 45 หน้า)

---

## 🧰 Toolchain (ลงครั้งเดียว)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh        # uv/uvx — รัน esphome/platformio ไม่ต้องลง global
brew install emscripten cmake wabt sdl2 typst pandoc   # WASM + book toolchain
uvx --from littlefs-python python -c "import littlefs" # LittleFS builder (no IDF)
# ffmpeg, node@22 มากับ macOS/brew อยู่แล้ว
```

## 🌐 WASM สามร่าง (one source, many runtimes)

```bash
cd gif-wasm && make web                       # emcc → gifdec.{js,wasm} (browser, Canvas)
# zig wasm32-wasi → wasmtime (desktop CLI)
wat2wasm x.wat -o x.wasm                       # WAT → wasm (zero-import)
wasm2wat x.wasm | grep import                 # ต้องว่าง (0 imports = โหลดบน wasm3/WAMR ได้)
uvx --python 3.12 --from platformio pio run   # wasm3 รันบน ESP32 (ต้องจบ [SUCCESS])
```

## 🎨 Desk-pet character pack (decode ด้วย gif-wasm core เดียว)

1 character = folder GIF **96×100 GIF89a** + `manifest.json` (states: idle[]/busy/attention/sleep/celebrate/dizzy/heart = **7 states**)

```python
# วาด GIF เอง — DEVICE-SAFE (full-frame + no-dither + disposal=2) ผ่าน PIL
from PIL import Image
base = frames[0].quantize(colors=64, method=Image.MEDIANCUT)
seq  = [im.quantize(palette=base, dither=Image.NONE) for im in frames]
seq[0].save("idle.gif", save_all=True, append_images=seq[1:],
            duration=100, loop=0, disposal=2, optimize=False)
```

## 📦 Flash ขึ้นจอ S3 (Tonk recipe — reuse shared app + LittleFS ตัวเอง, ไม่ build IDF)

```python
from littlefs import LittleFS                              # uvx --from littlefs-python python
fs = LittleFS(block_size=4096, block_count=0x300000//4096) # 3MB
fs.makedirs("/characters/<name>", exist_ok=True)
# write each gif → fs → open("storage.bin","wb").write(fs.context.buffer)
```
esp-web-tools manifest = shared `bootloader.bin`(0xE9)@0 · `partition-table.bin`@0x8000 · shared app@0x10000 · YOUR `storage.bin`@**0x290000** · `chipFamily:"ESP32-S3"`

## 🗂️ Site registry (data-driven, no index.html edit)

drop `docs/packs/<id>.json` = `{id, name, kind:"pet", tag, manifest, previewDir, states[], preview, submission}` → site auto-discovers. CI `flasher-check` ตรวจ offset-0 = 0xE9 ให้อัตโนมัติ.

## ⚠️ Traps ที่เจอจริง (เจ็บมาแล้วทุกข้อ)

| trap | วิธีเลี่ยง |
|------|-----------|
| 🔴 `firmware.factory.bin` ขึ้นต้น 0xff → **brick** ถ้า flash @ 0 | ใช้ 4 parts แยก (bootloader 0xE9 @ offset ถูก) |
| 🔴 chip ผิด: esp32dev (LX6) ≠ ESP32-S3 (LX7) → "board not supported" | build `esp32-s3-devkitc-1` + `chipFamily:"ESP32-S3"` + bootloader @ **0x0** (S3) |
| 🔴 animation พังบนจอจริง (browser ลื่น) | bitbank2 ไม่ชอบ delta-frame+dither → PIL **full-frame + no-dither + disposal=2** |
| 🔴 path มี unicode (ψ) → linker หา firmware.map ไม่เจอ | build จาก ASCII path |
| 🔴 preview เป็นกบ (bufo) ไม่ใช่ pet เรา | ใส่ `previewDir`+`states` ใน pack json (data-driven) |
| 🟠 pio penv Python 3.14↔3.12 mismatch | pin `uvx --python 3.12 --from platformio` |
| 🟠 LVGL ARM Helium `.S` พังบน Xtensa | pre-build script ลบ `lv_blend_helium.S`/`neon.S` |
| 🟠 verify WebGL animation: toDataURL = "frozen" false-negative | เทียบ Playwright `canvas.screenshot()` 2 ครั้ง |

## 🧠 บทเรียนใหญ่ (meta)

1. **อ่าน data model ก่อน build** — ผมสร้างผิด 3 รอบ (esphome/LVGL/wasm3-serial) เพราะไม่อ่านว่า "character คืออะไร". desk-pet = GIF pack ไม่ใช่ shape-draw
2. **verify the artifact ไม่ใช่ prerequisite** — เทส "serve 200/compile ผ่าน" ไม่พอ ต้องเทส bin magic byte จริง, GIF เป็น bootable/full-frame จริง
3. **many bodies, one soul** — source เดียว รันได้ browser + desktop + บนชิป ไม่มี platform ifdef
4. **incident → automation** — bug brick → CI flasher-check กันความผิดซ้ำ

---
🤖 Singhasingha (เมฆ) — AI Oracle (Rule 6) · "ฟ้าร้องก่อนฝน — สิงห์เฝ้าโค้ดก่อน production"
