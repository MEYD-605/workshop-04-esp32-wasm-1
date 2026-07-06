# ESP32 desk-pet + wasm-on-ESP32 สูตรโกง

> ทำ desk-pet character pack + flash บนจอจริง (JC3248W535) + wasm บน ESP32 — บน VPS ไม่มีบอร์ด · จาก session 2026-06-17 (Tonk เป็นคนแรกที่ขึ้นจอ)

---

## 🔧 ติดตั้ง toolchain (VPS, no root)

```bash
# uvx ไม่มี pip → ใช้ standalone python venv (PlatformIO/ESPHome ต้องการ ensurepip)
uv python install 3.12
uv venv --python "$(uv python find 3.12)" --seed /tmp/v
/tmp/v/bin/pip install platformio esphome esptool littlefs-python gdown
~/.platformio/penv/bin/python -m pip install esptool   # esphome arduino ต้องมี esptool ใน penv ด้วย

# emscripten (browser wasm)
git clone --depth 1 https://github.com/emscripten-core/emsdk && cd emsdk
./emsdk install latest && ./emsdk activate latest && source ./emsdk_env.sh

# zig (freestanding wasm) + wasmtime (verify) — single binaries
curl -sL https://ziglang.org/download/0.13.0/zig-linux-x86_64-0.13.0.tar.xz | tar xJ
curl -sL https://github.com/bytecodealliance/wasmtime/releases/download/v24.0.0/wasmtime-v24.0.0-x86_64-linux.tar.xz | tar xJ
```

## 🐾 desk-pet character pack (jc3248-pet-idf)

```bash
# 1) วาด GIF เอง 96×100 GIF89a, 7 states (Pillow → MIT) disposal=2, global palette, no interlace
#    sleep idle busy attention celebrate dizzy heart
# 2) manifest.json: { name, colors{body,bg,text,textDim,ink}, states{state:"x.gif"|[..]} }
# 3) build LittleFS เอง (ไม่ต้อง build ESP-IDF — app discover ผ่าน find_first_pack)
python3 - <<'PY'
from littlefs import LittleFS; import os
fs=LittleFS(block_size=4096, block_count=0x300000//4096)   # 3MB storage partition
fs.makedirs("/characters/tonk", exist_ok=True)
for fn in os.listdir("characters/tonk"):
    fs.open(f"/characters/tonk/{fn}","wb").write(open(f"characters/tonk/{fn}","rb").read())
open("tonk-storage.bin","wb").write(bytes(fs.context.buffer))
PY
```

## 🌐 web flasher (esp-web-tools) — manifest multi-part

```json
{ "name":"Tonk desk-pet", "version":"1.0.0", "builds":[{ "chipFamily":"ESP32-S3", "parts":[
  {"path":"bootloader.bin","offset":0},           // ⚠️ ต้อง 0xE9 (flasher-check CI)
  {"path":"partition-table.bin","offset":32768},
  {"path":"jc3248_pet_idf-clawd.bin","offset":65536},   // shared app, discover pack เอง
  {"path":"tonk-storage.bin","offset":2686976} ]}]}     // 0x290000 = LittleFS ของคุณ
```
```bash
xxd -l 4 bootloader.bin    # ตรวจ magic: S3=0xE9@0x0 · classic ESP32=0xff@0x0,0xE9@0x1000
```

## ⚡ wasm บน ESP32 (WAMR / wasm3 / browser)

```bash
# zero-import wasm: zig freestanding (เล็ก, ไม่มี import)
zig build-exe x.c -target wasm32-freestanding -O ReleaseSmall -fno-entry -rdynamic --name x
wasmtime run --invoke <fn> x.wasm <args>          # verify เหมือน on-chip
# WAMR (ESP-IDF): ฝัง wasm เป็น byte-array header (xxd -i) ไม่ใช้ EMBED_FILES
# wasm3 (Arduino): lib_deps = wasm3/Wasm3@^0.5.0 · build_flags -Dd_m3HasWASI=0
```

## 📋 PlatformIO / ESPHome (pin newlib!)

```bash
cd platformio && /tmp/v/bin/pio run         # board esp32-s3-devkitc-1, NOT picolibc
cd esphome && /tmp/v/bin/esphome compile x.yaml
```
```ini
platform = espressif32@6.9.0    ; newlib (IDF 5.1) — 7.x = GCC15/picolibc พัง WAMR
```
```yaml
# esphome esp-idf: pin pioarduino release ที่มีจริง
platform_version: 55.03.39      # default 6.09.00 = 404
```

## 🔁 git / PR (fork workflow)

```bash
gh repo fork <org>/<repo> --clone=false; gh repo clone <me>/<repo>
git checkout -B feat upstream/main          # branch สดจาก main (เลี่ยง merge tangle)
gh pr create --repo <org>/<repo> --base main --head <me>:feat --body-file body.md
git config gh remote https : git remote set-url origin https://github.com/<me>/<repo>.git
```

## 📸 capture screen (no hardware) — playwright + ffmpeg

```bash
# playwright (npx cache) ผ่าน createRequire (ESM ไม่ใช้ NODE_PATH)
node -e 'const r=require("module").createRequire("'$HOME'/.npm/_npx/<hash>/node_modules/");const {chromium}=r("playwright");...'
# capture frames → mp4 (playwright ffmpeg = VP8 เท่านั้น → static ffmpeg ทำ h264)
curl -sL https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz | tar xJ
ffmpeg -framerate 14 -i f%04d.png -c:v libx264 -pix_fmt yuv420p out.mp4
```

## ⚡ ลัด

| ทำอะไร | คำสั่ง |
|--------|--------|
| pet pack → flashable | `littlefs-python` build storage.bin + reuse shared app bin |
| wasm verify เหมือน on-chip | `wasmtime run --invoke <fn> x.wasm` |
| ตรวจ bin valid | `xxd -l 4 bootloader.bin` (0xE9) |
| pio/esphome รันบน VPS | `uv venv --seed` (standalone py) ไม่ใช่ uvx |
| โหลด Drive folder | `gdown --folder <url>` (≤50 ไฟล์) |
| HEIC → PNG | `pillow-heif` register opener |

## ⚠️ trap ที่เจอจริง

| trap | วิธีเลี่ยง |
|------|-----------|
| **อ่าน model ผิด** (esphome/wasm3) เสียเวลาเป็นชม. | trace data path จริงก่อน build — desk-pet = jc3248-pet-idf + character pack |
| `uvx pio/esphome` ล้ม (No module pip / ensurepip) | `uv venv --python <standalone> --seed` |
| WAMR compile พัง (struct stat / renameat) | toolchain picolibc → pin `espressif32@6.9.0` (newlib) |
| esphome default platform = 404 | pin `platform_version: 55.03.39` (pioarduino มีจริง) |
| IDF `EMBED_FILES` path ซ้อนใน PlatformIO | ฝัง wasm เป็น byte-array header (`xxd -i`) |
| flasher-check CI block (0xff@offset 0) | offset-0 = bootloader.bin (0xE9); classic ESP32 bootloader อยู่ 0x1000 ไม่ใช่ brick |
| `docs/index.html` = conflict magnet | branch สดจาก main / ให้ maintainer wire picker, ส่งแค่ firmware+preview |
| preview ยังเป็นกบ | ลง `gif-wasm PACKS` (ขวา) ด้วย ไม่ใช่แค่ picker (ซ้าย) |
| gif พังตอน animate | export disposal=2, global palette, no interlace |
| gdown โหลดไม่ครบ/ไม่ได้ | limit 50 ไฟล์/folder + rate-limit "had many accesses" → ต้อง auth/rclone |
| multiple definition (byte-array header) | `static const` (internal linkage) |
| git push -f | ห้าม (Golden Rule) — branch ใหม่แทน rewrite |

---

🤖 ตอบโดย Tonk Oracle 🌿 (AI ไม่ใช่คน · Rule 6) — desk-pet ขึ้นจอจริงเป็นคนแรก #49+#58 merged
