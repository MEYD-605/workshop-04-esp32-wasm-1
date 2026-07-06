# Nova's Desk-Pet Cheatsheet 🐾

> Copy-paste commands for building, verifying, and shipping a desk-pet character pack
> Oracle: Nova 🔮 | Workshop 04 | 2026-06-17

---

## 1. GIF Pipeline (Python/Pillow)

```bash
pip install Pillow

python3 -c "
from PIL import Image, ImageDraw
# ... use your art script ...
# Key rules:
# - quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
# - disposal=2 (full frame, NOT partial)
# - frame_duration=150ms
# - loop=0 (infinite)
"
```

**3 traps**:
- `quantize` without `dither=NONE` → blurry pixel art
- `disposal != 2` → ghost frames (tail doubles)
- `loop != 0` → animation stops after N loops

---

## 2. LittleFS Storage Image

```bash
pip install littlefs-python

python3 -c "
from littlefs import LittleFS
fs = LittleFS(block_size=4096, block_count=768, name_max=255)
fs.mkdir('/characters')
fs.mkdir('/characters/novamon')
for state in ['idle','busy','attention','celebrate','dizzy','sleep','heart']:
    with open(f'{state}.gif','rb') as f:
        fs.write_file(f'/characters/novamon/{state}.gif', f.read())
with open('manifest.json','rb') as f:
    fs.write_file('/characters/novamon/manifest.json', f.read())
with open('novamon-storage.bin','wb') as f:
    f.write(fs.to_bytes())
print(f'Size: {len(fs.to_bytes()):,} bytes')
# Expected: 3,145,728 bytes (3MB)
"
```

**Critical**: `block_size=4096` — must match ESP32-S3 flash erase block (4KB). Any other value = flash fails.

---

## 3. Verify Before PR (3-Layer Gate)

### Layer 1: GIF Decode
```bash
python3 -c "
from PIL import Image
for state in ['idle','busy','attention','celebrate','dizzy','sleep','heart']:
    img = Image.open(f'{state}.gif')
    print(f'{state}: {img.size} {img.n_frames}f')
# Expected: 7/7, 96x100, multi-frame
"
```

### Layer 2: LittleFS Proof
```bash
python3 -c "
from littlefs import LittleFS
fs = LittleFS(block_size=4096, block_count=768)
with open('novamon-storage.bin','rb') as f:
    fs.from_bytes(f.read())
for entry in fs.listdir('/characters/novamon'):
    print(entry.name, entry.size)
# Expected: 8 entries (7 GIF + manifest)
"
```

### Layer 3: byte0 check
```bash
xxd -l 1 novamon-storage.bin
# 00000000: e9  ← MUST be 0xE9 (LittleFS magic)
# If 0xFF → it's firmware, NOT storage → will brick
```

---

## 4. Web Flasher Registration

`docs/packs/novamon.json`:
```json
{
  "id": "novamon",
  "name": "Novamon",
  "author": "Nova Oracle x หนุ่ม",
  "kind": "pet",
  "previewDir": "characters/novamon",
  "states": ["idle","busy","attention","celebrate","dizzy","sleep","heart"],
  "description": "Digimon-style cyber-puppy desk-pet"
}
```

**Trap**: Missing `previewDir` + `states` → preview shows bufo (frog fallback) silently.

---

## 5. Git Workflow

```bash
# Fork (one-time)
git clone https://github.com/YOUR_USER/workshop-04-esp32-wasm
cd workshop-04-esp32-wasm
git remote add upstream https://github.com/the-oracle-keeps-the-human-human/workshop-04-esp32-wasm

# New submission
mkdir -p submissions/07-nova/{book,characters,knowledge}
# ... add files ...

# Commit
git add submissions/07-nova/
git commit -m "feat(nova): desk-pet pack + books + knowledge"
git push origin main
```

---

## 6. Book Render (fpdf2 fallback)

```bash
pip install fpdf2

python3 render-pdf.py
# fpdf2 + Tahoma — works on Windows without typst/pandoc/XeLaTeX
# Output: Many-Bodies-One-Soul-Novamon.pdf (~33pp)
```

---

## 7. Common Friction Points

| Symptom | Cause | Fix |
|---------|-------|-----|
| Preview shows frog | `previewDir` not in `docs/packs/<id>.json` | Register pack metadata |
| GIF colors wrong | Auto-convert RGBA→P without quantize | `quantize(256, MEDIANCUT, Dither.NONE)` |
| Ghost frames | Partial frames in GIF | `disposal=2` (full frame) every frame |
| Flash fails | Wrong `block_size` | `block_size=4096` always |
| brick after flash | `byte0 = 0xFF` (firmware flashed to storage) | Check `xxd -l 1` before flash |
| PR closed | Format changed since last read | Grep latest merged PR before push |
| `gh` CLI 127 | Not installed on Windows | Use `curl -H "Authorization: token"` to GitHub API |

---

> **Nova's Rule**: Verify before push. Read before code. Ask before guessing.
